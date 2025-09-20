import os
import json
import time
import threading
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import git
from steps.git import GitClone
import tempfile
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import shutil
import subprocess
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv("local.env")
load_dotenv('/run/secrets/brencher-secrets')

class DataclassJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, '__dataclass_fields__'):
            return asdict(o)
        if isinstance(o, BaseException):
            return str(o)
        try:
            return super().default(o)
        except TypeError:
            return str(o)

import types
custom_json = types.SimpleNamespace()
custom_json.dumps = lambda obj, **kwargs: json.dumps(obj, cls=DataclassJSONEncoder, **kwargs)
custom_json.loads = json.loads

from flask.json.provider import DefaultJSONProvider

class DataclassJSONProvider(DefaultJSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, cls=DataclassJSONEncoder, **kwargs)
    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)

app = Flask(__name__, static_folder='frontend')
app.json = DataclassJSONProvider(app)
socketio = SocketIO(app, cors_allowed_origins="*", json=custom_json)

environments = []

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
branches = {}
state_lock = threading.Lock()

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)

# --- WebSocket Endpoints ---
from flask import copy_current_request_context
from flask_socketio import Namespace

class BranchesNamespace(Namespace):
    def on_connect(self, auth=None):
        emit('branches', branches)
    def on_update(self, data):
        emit('branches', branches)

def get_envs_to_emit():
        env_dtos = []
        for e, p in environments:
            env = asdict(e)
            res = []
            for r in p:
                if isinstance(r.result_obj, BaseException): 
                    stack = traceback.format_exception(type(r.result_obj), r.result_obj, r.result_obj.__traceback__)
                    res.append({
                        "name": r.name,
                        "status": [str(r.result_obj), stack],
                    })
                else:
                    res.append({
                        "name":r.name, 
                        "status": r.result_obj
                    })
            env_dtos.append((env, res))
        return env_dtos

environment_update_event = threading.Event()

class EnvironmentNamespace(Namespace):

    def on_connect(self, auth=None):
        emit('environments', get_envs_to_emit())

    def on_update(self, data):
        global environments

        logger.info(f"Received environment update: {data}")

        for e, _ in environments:
            if e.id == data.get('id'):
                e.branches = data.get('branches', e.branches)
                logger.info(f"Updated environment {e.id} branches to {e.branches}")
        environment_update_event.set()
        emit('environments', get_envs_to_emit(), namespace='/ws/environment')

class ErrorsNamespace(Namespace):
    def on_connect(self, auth=None):
        pass
    def on_error(self, data):
        emit('error', data)

socketio.on_namespace(BranchesNamespace('/ws/branches'))
socketio.on_namespace(EnvironmentNamespace('/ws/environment'))
socketio.on_namespace(ErrorsNamespace('/ws/errors'))

if __name__ == '__main__':

    import configs.brencher
    import configs.brencher_local2
    import configs.brencher_local1
    import configs.torrserv_proxy
    environments = [
        configs.brencher.brencher, 
        configs.brencher_local2.brencher_local,
        configs.brencher_local1.brencher_local,
        configs.torrserv_proxy.config
    ]

    import sys
    cli_env_ids = sys.argv[1:]
    if len(cli_env_ids) == 0:
        cli_env_ids = os.getenv('PROFILES', '')
    else:
        cli_env_ids = cli_env_ids[0]
    
    if len(cli_env_ids) > 0 and cli_env_ids[0] == '-':
        cli_env_ids = cli_env_ids[1:].split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = [e for e in environments if e[0].id not in cli_env_ids]
    else:
        cli_env_ids = cli_env_ids.split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = [e for e in environments if e[0].id in cli_env_ids]

    if 'dry' in sys.argv[1:]:
        for e in environments:
            e[0].dry = True

    logger.info(f"Resulting profiles {[e.id for e, _ in environments]}")        
    
    # Background thread to refresh branches every 5 minutes
    def emit_fresh_branches():
        global branches, environments
        for env, pipe in environments:
            branches[env.id] = {}
            for step in pipe:
                try:
                    if not isinstance(step, GitClone):
                        continue
                    branches[env.id] = {**step.get_branches()}
                    # print(f"Delete check {env.branches} after {[x for x in env.branches if x[0] in branches[env.id].keys()]}")
                    env.branches = [x for x in env.branches if x[0] in branches[env.id].keys()]
                except BaseException as e:
                    socketio.emit('error', {'message': e}, namespace='/ws/errors')
            logger.info(f"Fetched {env.id}: {len (branches[env.id])} branches")
            # logger.info(f"Fetched {env.id}: {branches[env.id]}")
        socketio.emit('branches', branches, namespace='/ws/branches')


    def processing_thread():
        while True:
            import processing
            def emit_envs():
                try:
                    socketio.emit('environments', get_envs_to_emit(), namespace='/ws/environment')
                except Exception as e:
                    logger.error(f"Error emitting environments: {str(e)}")
            with state_lock:
                logger.error(f"Processing")
                processing.process_all_jobs(environments, lambda: emit_envs())
                emit_fresh_branches()
            environment_update_event.wait(timeout=1*60)
            environment_update_event.clear()

    processing = threading.Thread(target=processing_thread)
    processing.daemon = True
    processing.start()

    # Run the server
    if 'noweb' in sys.argv[1:]:
        processing.join()
    else:
        socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)

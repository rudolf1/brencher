import os
import json
import time
import threading
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
import git
import tempfile
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
import shutil
import subprocess

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

import configs.brencher
import configs.brencher_local
environments = [configs.brencher.brencher, configs.brencher_local.brencher_local]
profiles = os.getenv('PROFILES', 'brencher_local').split(',')
environments = [e for e in environments if e[0].id in profiles]

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
branches = {}
state_lock = threading.Lock()

def fetch_branches():

    for e, _ in environments:
        url = e.repo
        protocol, rest = url.split('://')
        # Get environment variables
        GIT_USERNAME = os.getenv('GIT_USERNAME', '')
        GIT_PASSWORD = os.getenv('GIT_PASSWORD', '')
        url = f"{protocol}://{GIT_USERNAME}:{GIT_PASSWORD}@{rest}"

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                repo = git.Repo.clone_from(url, tmp_dir, bare=True)
                # Specify refspec to fetch all branches
                fetch_info = repo.remotes.origin.fetch(refspec='+refs/heads/*:refs/remotes/origin/*')
                
                # Extract branch names
                new_branches = []
                for ref in repo.refs:
                    if ref.name.startswith('origin/') and not ref.name.startswith('origin/HEAD'):
                        branch_name = ref.name[len('origin/'):]
                        if not branch_name.startswith('auto/'):  # Skip auto branches
                            new_branches.append(branch_name)
                
                branches[e.id] = new_branches
                logger.info(f"Fetched {e.id}:{len(new_branches)} branches")
                
        except Exception as e:
            error_msg = f"Failed to fetch branches: {str(e)}"
            logger.error(error_msg)
            socketio.emit('error', {'message': error_msg}, namespace='/ws/errors')

# API Routes
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
                    res.append({
                        "name":r.name, 
                        "status": str(r.result_obj)
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
                e.state = data.get('state', e.state)
                e.branches = data.get('branches', e.branches)
                logger.info(f"Updated environment {e.id} state to {e.state} and branches to {e.branches}")
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
    # Background thread to refresh branches every 5 minutes
    def branch_refresh_thread():
        while True:
            fetch_branches()
            socketio.emit('branches', branches, namespace='/ws/branches')
            time.sleep(300)  # 5 minutes

    # Start branch refresh thread
    refresh_thread = threading.Thread(target=branch_refresh_thread)
    refresh_thread.daemon = True
    refresh_thread.start()

    def processing_thread():
        while True:
            import processing
            def emit_envs():
                try:
                    socketio.emit('environments', get_envs_to_emit(), namespace='/ws/environment')
                except Exception as e:
                    logger.error(f"Error emitting environments: {str(e)}")
            processing.do_job(environments, lambda: emit_envs())
            environment_update_event.wait(timeout=1000)
            environment_update_event.clear()

    processing = threading.Thread(target=processing_thread)
    processing.daemon = True
    processing.start()

    # Run the server
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)

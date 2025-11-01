from multiprocessing import Pipe
import os
import json
import time
import threading
import hashlib
from flask import Flask, request, jsonify, send_from_directory
from steps.step import AbstractStep
from flask_socketio import SocketIO, emit
import socketio as socketio_client
from dotenv import load_dotenv
import git
import enironment
from steps.git import GitClone
import tempfile
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
import shutil
import subprocess
import traceback
from typing import TypeVar

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

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
environments: Dict[str, Tuple[enironment.Environment, List[AbstractStep]]] = {}
environments_slaves: Dict[str, Tuple[enironment.Environment, List[AbstractStep]]] = {}
branches = {}
branches_slaves = {}
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

T = TypeVar('T')
def merge_dicts(a: Dict[str, T], b: Dict[str, T]) -> Dict[str, T]:
    result: Dict[str, T] = {}
    for k in (a.keys() | b.keys()):
        if k not in a or k not in b:
            result[k] = a.get(k, b.get(k))  # type: ignore[arg-type]
            continue
        if (
            isinstance(a[k], dict)
            and isinstance(b[k], dict)
        ):
            result[k] = merge_dicts(a[k], b[k])  # type: ignore[arg-type]
        else:
            result[k] = b[k]
    return result

slave_url = os.getenv('SLAVE_BRENCHER')
remote_sio: socketio_client.Client | None = None
if slave_url:
    logger.info(f"SLAVE_BRENCHER set, will connect to master at {slave_url}")
    remote_sio = socketio_client.Client(logger=False, engineio_logger=False)

    def _mark_forwarded(payload):
        if isinstance(payload, dict):
            return {**payload, '_slave_forwarded': True}
        return {'_slave_forwarded': True, '__payload': payload}

    # Handlers for events from master -> re-emit locally (marked so we don't loop)
    @remote_sio.on('branches', namespace='/ws/branches')
    def _remote_branches(data):
        global branches, branches_slaves
        branches_slaves = data
        merge_result = merge_dicts(branches, branches_slaves)
        try:
            socketio.emit('branches', _mark_forwarded(merge_result), namespace='/ws/branches')
        except Exception as e:
            logger.error(f"Error forwarding remote branches locally: {e}")

    @remote_sio.on('environments', namespace='/ws/environment')
    def _remote_environments(data):
        global environments, environments_slaves
        environments_slaves = data
        try:
            socketio.emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')
        except Exception as e:
            logger.error(f"Error forwarding remote environments locally: {e}")

    @remote_sio.on('error', namespace='/ws/errors')
    def _remote_error(data):
        try:
            socketio.emit('error', _mark_forwarded(data), namespace='/ws/errors')
        except Exception as e:
            logger.error(f"Error forwarding remote errors locally: {e}")

    @remote_sio.event
    def connect():
        logger.info("Connected to master brencher (SLAVE mode).")

    @remote_sio.event
    def disconnect():
        logger.info("Disconnected from master brencher (SLAVE mode).")


class BranchesNamespace(Namespace):
    def on_connect(self, auth=None):
        emit('branches', merge_dicts(branches, branches_slaves))
    def on_update(self, data):
        emit('branches', merge_dicts(branches, branches_slaves))

def get_local_envs_to_emit() -> Dict[str, Tuple[enironment.Environment, List[AbstractStep]]]:
        env_dtos = {}
        for e, p in environments.values():
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
            env_dtos[env['id']] = (env, res)
        return env_dtos

def get_global_envs_to_emit():
    global environments, environments_slaves
    local_envs = get_local_envs_to_emit()
    merge_result = merge_dicts(local_envs, environments_slaves)
    logger.info(f"Local keys: {local_envs.keys()}")
    logger.info(f"Slave keys: {environments_slaves.keys()}")
    common_keys = set(local_envs.keys()) & set(environments_slaves.keys())
    if len(common_keys) > 0:
        socketio.emit('error', {'message': f"Conflict: both master and slave have environment with id {common_keys}"}, namespace='/ws/errors')
    return merge_result

environment_update_event = threading.Event()

class EnvironmentNamespace(Namespace):

    def on_connect(self, auth=None):
        emit('environments', get_global_envs_to_emit())

    def on_update(self, data):
        global environments, remote_sio

        logger.info(f"Received environment update: {data}")

        for e, _ in environments.values():
            if e.id == data.get('id'):
                e.branches = data.get('branches', e.branches)
                logger.info(f"Updated environment {e.id} branches to {e.branches}")

        environment_update_event.set()

        if remote_sio is not None and remote_sio.connected:
            remote_sio.emit('update', data, namespace='/ws/environment')
            logger.info(f"Updated slave")

        emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')

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
    import configs.brencher2
    import configs.brencher_local2
    import configs.brencher_local1
    import configs.torrserv_proxy
    import configs.immich
    environments_l = [
        configs.brencher.brencher, 
        configs.brencher2.brencher,
        configs.brencher_local2.brencher_local,
        configs.brencher_local1.brencher_local,
        configs.torrserv_proxy.config,
        configs.immich.config,
    ]
    environments = {e[0].id: e for e in environments_l}

    import sys
    cli_env_ids = sys.argv[1:]
    if len(cli_env_ids) == 0:
        cli_env_ids = os.getenv('PROFILES', '')
    else:
        cli_env_ids = cli_env_ids[0]
    logger.info(f"cli_env_ids {cli_env_ids}")        
    if len(cli_env_ids) > 0 and cli_env_ids[0] == '-':
        cli_env_ids = cli_env_ids[1:].split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        logger.info(f"cli_env_ids (minus) {cli_env_ids}")        
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = { k: e for k, e in environments.items() if k not in cli_env_ids }
    else:
        cli_env_ids = cli_env_ids.split(',')
        cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
        logger.info(f"cli_env_ids {cli_env_ids}")        
        if cli_env_ids and len(cli_env_ids) > 0:
            environments = { k: e for k, e in environments.items() if k in cli_env_ids }

    if 'dry' in sys.argv[1:]:
        for id, e in environments.items():
            e[0].dry = True

    logger.info(f"Resulting profiles {environments.keys()}")        
    
    # Background thread to refresh branches every 5 minutes
    def emit_fresh_branches():
        global branches, environments
        for k, e in environments.items():
            env, pipe = e
            branches[k] = {}
            for step in pipe:
                try:
                    if not isinstance(step, GitClone):
                        continue
                    branches[k] = {**step.get_branches()}
                    # logger.info(f"Delete check {env.branches} after {[x for x in env.branches if x[0] in branches[env.id].keys()]}")
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
                    socketio.emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')
                except Exception as e:
                    logger.error(f"Error emitting environments: {str(e)}")
            with state_lock:
                logger.error(f"Processing")
                processing.process_all_jobs(list(environments.values()), lambda: emit_envs())
                emit_fresh_branches()
            environment_update_event.wait(timeout=1*60)
            environment_update_event.clear()


    processing = threading.Thread(target=processing_thread)
    processing.daemon = True
    processing.start()


        # Connect in background so server startup isn't blocked
    def _connect_remote():
        global remote_sio
        print("Connecting to SLAVE_BRENCHER...")
        while True:
            try:
                if remote_sio is not None and not remote_sio.connected:
                    remote_sio.connect(slave_url, namespaces=['/ws/branches', '/ws/environment', '/ws/errors'])
            except Exception as e:
                logger.error(f"Could not connect to SLAVE_BRENCHER {slave_url}: {e}")
            time.sleep(60)

    t = threading.Thread(target=_connect_remote, daemon=True)
    t.start()

    if 'noweb' in sys.argv[1:]:
        processing.join()
    else:
        socketio.run(app, host='0.0.0.0', port=5001, debug=False, allow_unsafe_werkzeug=True)

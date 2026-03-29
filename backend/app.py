import json
import logging
import os
import threading
import time
import traceback
import types
from dataclasses import asdict, replace
from typing import List, Dict, Any, Optional
from typing import TypeVar

import socketio as socketio_client
from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_socketio import SocketIO, emit

from configs.gmail_mcp import gmail_mcp
from enironment import Environment, wrap_in_cached
from processing import reset_caches
from steps.git import GitClone
from steps.step import CachingStep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger('werkzeug').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv("local.env")
load_dotenv('/run/secrets/brencher-secrets')


class DataclassJSONEncoder(json.JSONEncoder):
	def default(self, o: Any) -> Any:
		if hasattr(o, '__dataclass_fields__'):
			return asdict(o)
		if isinstance(o, BaseException):
			return str(o)
		try:
			return super().default(o)
		except TypeError:
			return str(o)


custom_json = types.SimpleNamespace()
custom_json.dumps = lambda obj, **kwargs: json.dumps(obj, cls=DataclassJSONEncoder, **kwargs)
custom_json.loads = json.loads


class DataclassJSONProvider(DefaultJSONProvider):
	def dumps(self, obj: Any, **kwargs: Any) -> str:
		return json.dumps(obj, cls=DataclassJSONEncoder, **kwargs)

	def loads(self, s: str | bytes, **kwargs: Any) -> Any:
		return json.loads(s, **kwargs)


app = Flask(__name__, static_folder='frontend')
app.json = DataclassJSONProvider(app)
socketio = SocketIO(app, cors_allowed_origins="*", json=custom_json)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
environments: Dict[str, Environment] = {}
environments_slaves: Dict[str, Environment] = {}
branches_slaves: Dict[str, Dict[str, Any]] = {}
state_lock = threading.Lock()


@app.route('/')
def serve_index() -> Any:
	return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:path>')
def serve_static(path: str) -> Any:
	return send_from_directory(FRONTEND_DIR, path)


# --- WebSocket Endpoints ---
from flask_socketio import Namespace

T = TypeVar('T')


def merge_dicts(a: Dict[str, T], b: Dict[str, T]) -> Dict[str, T]:
	result: Dict[str, T] = {}
	for k in (a.keys() | b.keys()):
		if k not in a or k not in b:
			result[k] = a.get(k, b.get(k))  # type: ignore[assignment]
			continue
		if (
				isinstance(a[k], dict)
				and isinstance(b[k], dict)
		):
			result[k] = merge_dicts(a[k], b[k])  # type: ignore[arg-type,assignment]
		else:
			result[k] = b[k]
	return result


slave_url = os.getenv('SLAVE_BRENCHER')
remote_sio = None
if slave_url:
	logger.info(f"SLAVE_BRENCHER set, will connect to master at {slave_url}")
	remote_sio = socketio_client.Client(logger=False, engineio_logger=False)


	# Handlers for events from master -> re-emit locally (marked so we don't loop)
	@remote_sio.on('branches', namespace='/ws/branches')
	def _remote_branches(data: Any) -> None:
		global branches_slaves
		branches_slaves = data
		try:
			socketio.emit('branches', get_global_branches_to_emit(), namespace='/ws/branches')
		except Exception as e:
			logger.error(f"Error forwarding remote branches locally: {e}")


	@remote_sio.on('environments', namespace='/ws/environment')
	def _remote_environments(data: Any) -> None:
		global environments_slaves
		environments_slaves = data
		try:
			socketio.emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')
		except Exception as e:
			logger.error(f"Error forwarding remote environments locally: {e}")


	@remote_sio.on('error', namespace='/ws/errors')
	def _remote_error(data: Any) -> None:
		try:
			socketio.emit('error', data, namespace='/ws/errors')
		except Exception as e:
			logger.error(f"Error forwarding remote errors locally: {e}")


	@remote_sio.event
	def connect() -> None:
		logger.info("Connected to master brencher (SLAVE mode).")


	@remote_sio.event
	def disconnect() -> None:
		logger.info("Disconnected from master brencher (SLAVE mode).")


class BranchesNamespace(Namespace):
	def on_connect(self, auth: Optional[Any] = None) -> None:
		emit('branches', get_global_branches_to_emit())

	def on_update(self, data: Any) -> None:
		emit('branches', get_global_branches_to_emit())


def get_local_envs_to_emit() -> Dict[str, Dict[str, Any]]:
	env_dtos: Dict[str, Dict[str, Any]] = {}
	for env in environments.values():
		pipeline_state: List[Dict[str, Any]] = []
		for r in env.pipeline:
			try:
				if isinstance(r, CachingStep):
					result = r._result
				else:
					result = r.progress()

				if isinstance(result, BaseException):
					stack = traceback.format_exception(type(result), result, result.__traceback__)
					pipeline_state.append({
						"name": r.name,
						"status": [str(result), stack],
						"error": True,
					})
				else:
					pipeline_state.append({
						"name": r.name,
						"status": result,
					})
			except BaseException as e:
				stack = traceback.format_exception(type(e), e, e.__traceback__)
				pipeline_state.append({
					"name": r.name,
					"status": [str(e), stack],
					"error": True,
				})
		env_dtos[env.id] = asdict(replace(env, pipeline=[]))
		env_dtos[env.id]['pipeline'] = pipeline_state
	return env_dtos


def get_global_envs_to_emit() -> Any:
	global environments, environments_slaves
	local_envs = get_local_envs_to_emit()
	merge_result = merge_dicts(local_envs, environments_slaves)  # type: ignore[misc]
	# logger.info(f"Local keys: {local_envs.keys()}")
	# logger.info(f"Slave keys: {environments_slaves.keys()}")
	common_keys = set(local_envs.keys()) & set(environments_slaves.keys())
	if len(common_keys) > 0:
		socketio.emit('error', {'message': f"Conflict: both master and slave have environment with id {common_keys}"},
		              namespace='/ws/errors')
	return merge_result


def get_local_branches_to_emit() -> Dict[str, Dict[str, List[Any]]]:
	global environments
	branches: Dict[str, Dict[str, List[Any]]] = {}
	for k, env in environments.items():
		branches[k] = {}
		try:
			for step in env.pipeline:
				if isinstance(step, GitClone):
					branches[k] = {**step.get_branches()}
				if isinstance(step, CachingStep) and isinstance(step.step, GitClone):
					branches[k] = {**step.step.get_branches()}
		except BaseException as e:
			logger.error(f"Error fetching branches for environment {env.id}: {str(e)}")

	return branches


def get_global_branches_to_emit() -> Dict[str, Dict[str, List[Any]]]:
	global branches_slaves
	local_branches: Dict[str, Dict[str, List[Any]]] = get_local_branches_to_emit()
	return merge_dicts(local_branches, branches_slaves)


environment_update_event = threading.Event()


@app.route('/state')
def serve_state() -> Any:
	return get_global_envs_to_emit()


@app.route('/branches')
def serve_branches() -> Any:
	return get_global_branches_to_emit()


class EnvironmentNamespace(Namespace):

	def on_connect(self, auth: Optional[Any] = None) -> None:
		emit('environments', get_global_envs_to_emit())

	def on_update(self, data: Dict[str, Any]) -> None:
		global environments, remote_sio

		logger.info(f"Received environment update: {data}")
		if data.get('id') == '':
			reset_caches(list(environments.values()))
		else:
			for env in environments.values():
				if env.id == data.get('id'):
					env.branches = data.get('branches', env.branches)
					logger.info(f"Updated environment {env.id} branches to {env.branches}")

		environment_update_event.set()

		if remote_sio and remote_sio is not None and remote_sio.connected:
			remote_sio.emit('update', data, namespace='/ws/environment')
			logger.info(f"Updated slave")

		emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')


class ErrorsNamespace(Namespace):
	def on_connect(self, auth: Optional[Any] = None) -> None:
		pass

	def on_error(self, data: Any) -> None:
		emit('error', data)


socketio.on_namespace(BranchesNamespace('/ws/branches'))
socketio.on_namespace(EnvironmentNamespace('/ws/environment'))
socketio.on_namespace(ErrorsNamespace('/ws/errors'))


def sigchld_handler(signum, frame):  # type: ignore[no-untyped-def]
	"""Reap zombie processes"""
	while True:
		try:
			pid, status = os.waitpid(-1, os.WNOHANG)
			if pid == 0:
				break
		except ChildProcessError:
			break


import signal


class App:

	def __init__(self, cli_env_ids_str: str, dry_run: bool = False) -> None:
		global environments
		# Register the handler
		signal.signal(signal.SIGCHLD, sigchld_handler)

		import configs.brencher
		import configs.brencher2
		import configs.brencher_local2
		import configs.brencher_local1
		import configs.torrserv_proxy
		import configs.immich
		import configs.registry
		import configs.gmail_mcp
		environments_l: List[Environment] = [
			configs.brencher.brencher,
			configs.brencher2.brencher2,
			configs.brencher_local2.brencher_local2,
			configs.brencher_local1.brencher_local1,
			configs.torrserv_proxy.torrserv_proxy,
			configs.immich.immich,
			configs.registry.registry,
			configs.gmail_mcp.gmail_mcp,
		]
		environments = {e.id: e for e in environments_l}

		logger.info(f"cli_env_ids {cli_env_ids_str}")
		if len(cli_env_ids_str) > 0 and cli_env_ids_str[0] == '-':
			cli_env_ids = cli_env_ids_str[1:].split(',')
			cli_env_ids = [x for x in cli_env_ids if len(x) > 0]
			logger.info(f"cli_env_ids (minus) {cli_env_ids}")
			if cli_env_ids and len(cli_env_ids) > 0:
				environments = {k: e for k, e in environments.items() if k not in cli_env_ids}
		else:
			cli_env_pairs = {x[0]: x[1] if len(x) > 1 else None for x in [x.split(":")
			                                                              for x in cli_env_ids_str.split(',')
			                                                              if len(x) > 0
			                                                              ]
			                 }
			logger.info(f"cli_env_ids {cli_env_pairs}")
			if cli_env_pairs and len(cli_env_pairs) > 0:
				environments = {k: e for k, e in environments.items() if k in cli_env_pairs.keys()}
				for k, v in cli_env_pairs.items():
					if v is not None:
						if k in environments:
							env = environments[k]
							env.branches = [(v, 'HEAD')]
							logger.info(f"Overriding environment {k} branches to {env.branches}")
						else:
							logger.warning(f"Environment {k} not found to override branches")
					else:
						logger.info(f"No branch override for environment {k}")
		if dry_run:
			for id, e in environments.items():
				e.dry = True

		logger.info(f"Resulting profiles {environments.keys()}")

		environments = {id: wrap_in_cached(e) for id, e in environments.items()}

	def processing_thread(self) -> None:
		while True:
			import processing
			def emit_envs() -> None:
				try:
					socketio.emit('branches', get_global_branches_to_emit(), namespace='/ws/branches')
				except Exception as e:
					logger.error(f"Error emitting branches: {str(e)}")
				try:
					socketio.emit('environments', get_global_envs_to_emit(), namespace='/ws/environment')
				except Exception as e:
					logger.error(f"Error emitting environments: {str(e)}")

			with state_lock:
				logger.info(f"Processing")
				if processing.process_all_jobs(list(environments.values()), lambda: emit_envs()):
					environment_update_event.wait(timeout=1 * 5)
				else:
					environment_update_event.wait(timeout=1 * 60)
				environment_update_event.clear()

	def _connect_remote(self) -> None:
		global remote_sio
		print("Connecting to SLAVE_BRENCHER...")
		while True:
			try:
				if remote_sio is not None and not remote_sio.connected:
					remote_sio.connect(slave_url, namespaces=['/ws/branches', '/ws/environment', '/ws/errors'])
			except Exception as e:
				logger.error(f"Could not connect to SLAVE_BRENCHER {slave_url}: {e}")
			time.sleep(60)

	def run(self) -> None:
		processing = threading.Thread(target=self.processing_thread)
		processing.daemon = True
		processing.start()

		t = threading.Thread(target=self._connect_remote, daemon=True)
		t.start()

	def runWeb(self, port: int) -> None:
		self.run()
		socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
	import os
	import sys

	cli_env_ids_list = sys.argv[1:]
	cli_env_ids_str: str
	if len(cli_env_ids_list) == 0:
		cli_env_ids_str = os.getenv('PROFILES', '')
	else:
		cli_env_ids_str = cli_env_ids_list[0]

	app1 = App(cli_env_ids_str, 'dry' in sys.argv[1:])
	app1.runWeb(port=(5007 if 'noweb' in sys.argv[1:] else 5001))

import asyncio
import json
import logging
import os
import signal
import sys
import threading
import traceback
from dataclasses import asdict, replace
from typing import Any, Dict, List, Optional, Set, TypeVar

import websockets
from dotenv import load_dotenv
from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from configs.gmail_mcp import gmail_mcp
from enironment import AbstractStep, Environment, wrap_in_cached
from processing import reset_caches
from steps.git import GitClone
from steps.step import CachingStep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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


def custom_json_dumps(obj: Any) -> str:
	return json.dumps(obj, cls=DataclassJSONEncoder)


app = FastAPI()

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

# In-memory state
environments: Dict[str, Environment] = {}
environments_slaves: Dict[str, Any] = {}
branches_slaves: Dict[str, Dict[str, Any]] = {}
state_lock = threading.Lock()

# Active WebSocket connections
ws_connections: Set[WebSocket] = set()

# Event loop reference for thread-safe async calls
_event_loop: Optional[asyncio.AbstractEventLoop] = None

# Slave connection state
slave_ws_task: Optional[asyncio.Task[None]] = None
slave_send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
slave_url = os.getenv('SLAVE_BRENCHER')

environment_update_event = threading.Event()


# --- Static File Serving ---

@app.get("/")
async def serve_index() -> FileResponse:
	return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


@app.get("/state")
async def serve_state() -> Response:
	return Response(content=custom_json_dumps(get_global_envs_to_emit()), media_type="application/json")


@app.get("/branches")
async def serve_branches_route() -> Response:
	return Response(content=custom_json_dumps(get_global_branches_to_emit()), media_type="application/json")


@app.get("/{path:path}")
async def serve_static(path: str) -> FileResponse:
	file_path = os.path.join(FRONTEND_DIR, path)
	if os.path.exists(file_path) and os.path.isfile(file_path):
		return FileResponse(file_path)
	return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))


# --- Utility Functions ---

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
	merge_result = merge_dicts(local_envs, environments_slaves)
	common_keys = set(local_envs.keys()) & set(environments_slaves.keys())
	if len(common_keys) > 0:
		_schedule_async(broadcast_error({'message': f"Conflict: both master and slave have environment with id {common_keys}"}))
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
			stack = traceback.format_exception(type(e), e, e.__traceback__)
			logger.error(f"Error fetching branches for environment {env.id}: {str(e)}\n{''.join(stack)}")

	return branches



def get_global_branches_to_emit() -> Dict[str, Dict[str, List[Any]]]:
	global branches_slaves
	local_branches: Dict[str, Dict[str, List[Any]]] = get_local_branches_to_emit()
	return merge_dicts(local_branches, branches_slaves)


# --- Async Helper for Calling from Sync Threads ---

def _schedule_async(coro: Any) -> None:
	"""Schedule a coroutine from a sync thread using the saved event loop."""
	if _event_loop is not None and _event_loop.is_running():
		asyncio.run_coroutine_threadsafe(coro, _event_loop)


# --- WebSocket Broadcasting Functions ---

async def broadcast(event: str, data: Any) -> None:
	"""Broadcast a message to all connected WebSocket clients that have not seen this data yet."""
	disconnected = set()
	message = custom_json_dumps({event: data})

	for websocket in list(ws_connections):
		if websocket.state.last_payloads.get(event) == message:
			continue
		try:
			await websocket.send_text(message)
			websocket.state.last_payloads[event] = message
		except Exception as e:
			logger.error(f"Error sending to websocket: {e}")
			disconnected.add(websocket)

	for ws in disconnected:
		ws_connections.discard(ws)


async def broadcast_branches(data: Any) -> None:
	await broadcast("branches", data)


async def broadcast_environments(data: Any) -> None:
	await broadcast("environments", data)


async def broadcast_error(data: Any) -> None:
	await broadcast("error", data)


# --- Single WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
	await websocket.accept()
	websocket.state.last_payloads: Dict[str, str] = {}
	ws_connections.add(websocket)

	try:
		# Send initial state on connect and record it so duplicate broadcasts are suppressed
		branches_payload = custom_json_dumps({"branches": get_global_branches_to_emit()})
		envs_payload = custom_json_dumps({"environments": get_global_envs_to_emit()})
		await websocket.send_text(branches_payload)
		websocket.state.last_payloads["branches"] = branches_payload
		await websocket.send_text(envs_payload)
		websocket.state.last_payloads["environments"] = envs_payload

		while True:
			data = await websocket.receive_text()
			message = json.loads(data)

			if "update" in message:
				update_data = message.get("update") or {}
				logger.info(f"Received environment update: {update_data}")

				if update_data.get('id') == '':
					reset_caches(list(environments.values()))
				else:
					for env in environments.values():
						if env.id == update_data.get('id'):
							env.branches = update_data.get('branches', env.branches)
							if 'dry' in update_data:
								env.dry = bool(update_data['dry'])
							logger.info(f"Updated environment {env.id} branches to {env.branches}, dry={env.dry}")

				environment_update_event.set()

				if slave_ws_task is not None:
					await slave_send_queue.put({"update": update_data})

				await broadcast_environments(get_global_envs_to_emit())

	except WebSocketDisconnect as e:
		ws_connections.discard(websocket)
	except Exception as e:
		logger.error(f"WebSocket error: {e}")
		await broadcast_error({'message': 'WebSocket exception'})
		ws_connections.discard(websocket)


# --- Slave Connection ---

async def connect_to_slave() -> None:
	"""Connect to a slave brencher instance via a single WebSocket."""
	global branches_slaves, environments_slaves

	if not slave_url:
		return

	logger.info(f"SLAVE_BRENCHER set, will connect to slave at {slave_url}")

	while True:
		try:
			ws_url = slave_url.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws'

			async with websockets.connect(ws_url) as ws:
				logger.info("Connected to slave WebSocket")

				async def handle_messages() -> None:
					global branches_slaves, environments_slaves
					async for msg in ws:
						parsed = json.loads(msg)
						if "branches" in parsed:
							branches_slaves = parsed["branches"]
							await broadcast_branches(get_global_branches_to_emit())
						elif "environments" in parsed:
							environments_slaves = parsed["environments"]
							await broadcast_environments(get_global_envs_to_emit())
						elif "error" in parsed:
							await broadcast_error(parsed["error"])

				async def handle_sends() -> None:
					while True:
						msg = await slave_send_queue.get()
						await ws.send(json.dumps(msg))

				await asyncio.gather(
					handle_messages(),
					handle_sends(),
				)

		except Exception as e:
			logger.error(f"Could not connect to SLAVE_BRENCHER {slave_url}: {e}")
			await asyncio.sleep(60)


# --- SIGCHLD Handler ---

def sigchld_handler(signum: int, frame: Any) -> None:
	"""Reap zombie processes."""
	while True:
		try:
			pid, status = os.waitpid(-1, os.WNOHANG)
			if pid == 0:
				break
		except ChildProcessError:
			break


# --- Startup Event ---

@app.on_event("startup")
async def startup_event() -> None:
	global _event_loop, slave_ws_task
	_event_loop = asyncio.get_event_loop()
	if slave_url:
		slave_ws_task = asyncio.create_task(connect_to_slave())


# --- App Class (used by CLI and integration tests) ---

class App:

	def __init__(self, cli_env_ids_str: str, dry_run: bool = False) -> None:
		global environments
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
				_schedule_async(broadcast_branches(get_global_branches_to_emit()))
				_schedule_async(broadcast_environments(get_global_envs_to_emit()))

			with state_lock:
				logger.info(f"Processing")
				if processing.process_all_jobs(list(environments.values()), lambda: emit_envs()):
					environment_update_event.wait(timeout=1 * 5)
				else:
					environment_update_event.wait(timeout=1 * 60)
				environment_update_event.clear()

	def run(self) -> None:
		processing = threading.Thread(target=self.processing_thread)
		processing.daemon = True
		processing.start()

	def runWeb(self, port: int) -> None:
		self.run()
		import uvicorn
		uvicorn.run(app, host='0.0.0.0', port=port, log_level='info')


if __name__ == '__main__':
	cli_env_ids_list = sys.argv[1:]
	cli_env_ids_str: str
	if len(cli_env_ids_list) == 0:
		cli_env_ids_str = os.getenv('PROFILES', '')
	else:
		cli_env_ids_str = cli_env_ids_list[0]

	app1 = App(cli_env_ids_str, 'dry' in sys.argv[1:])
	app1.runWeb(port=(5007 if 'noweb' in sys.argv[1:] else 5001))

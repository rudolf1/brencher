import asyncio
import json
import logging
import os
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, List, Optional, TypeVar

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import App
from utils import custom_json_dumps
from secondary import SecondaryManager

logger = logging.getLogger(__name__)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '../frontend')

T = TypeVar('T')


def _merge_dicts(a: Dict[str, T], b: Dict[str, T]) -> Dict[str, T]:
	result: Dict[str, T] = {}
	for k in (a.keys() | b.keys()):
		if k not in a or k not in b:
			result[k] = a.get(k, b.get(k))  # type: ignore[assignment]
			continue
		if (
				isinstance(a[k], dict)
				and isinstance(b[k], dict)
		):
			result[k] = _merge_dicts(a[k], b[k])  # type: ignore[arg-type,assignment]
		else:
			result[k] = b[k]
	return result


class WebApp:

	def __init__(self, core: App, port: int) -> None:
		self.core = core
		self.port = port

		self.ws_connections: Dict[WebSocket, Dict[str, Any]] = {}
		self._event_loop: Optional[asyncio.AbstractEventLoop] = None
		self._server: Any = None
		self.secondaryManager: Optional[SecondaryManager] = None
		
		@asynccontextmanager
		async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
			self._event_loop = asyncio.get_running_loop()
			self.secondaryManager = SecondaryManager(
				urls=os.getenv("SECONDARY_BRENCHER", ""),
				on_update=lambda: self.broadcast_all(),
			)
			yield

		self.app = FastAPI(lifespan=lifespan)
		self.app.add_middleware(
			CORSMiddleware,
			allow_origins=["*"],
			allow_credentials=True,
			allow_methods=["*"],
			allow_headers=["*"],
		)

		self.app.get("/")(self.serve_index)
		self.app.get("/state")(self.serve_state)
		self.app.get("/branches")(self.serve_branches_route)
		self.app.get("/{path:path}")(self.serve_static)
		self.app.websocket("/ws")(self.websocket_endpoint)

	# --- State assembly (local + secondary) ---

	def get_global_envs_to_emit(self) -> Any:
		local_envs = self.core.get_local_envs_to_emit()
		merged: Dict[str, Any] = local_envs
		for connector in self.secondaryManager or []:
			v = connector.environments
			common_keys = set(merged.keys()) & set(v.keys())
			if len(common_keys) > 0:
				self._schedule_async(self.broadcast_error({'message': f"Conflict: both master and secondary have environment with id {common_keys}"}))
			merged = _merge_dicts(merged, v)
		return merged

	def get_global_branches_to_emit(self) -> Dict[str, Dict[str, List[Any]]]:
		local_branches: Dict[str, Dict[str, List[Any]]] = self.core.get_local_branches_to_emit()
		merged: Dict[str, Dict[str, List[Any]]] = local_branches
		for connector in self.secondaryManager or []:
			merged = _merge_dicts(merged, connector.branches)
		return merged

	# --- Async scheduling from sync callbacks ---

	def _schedule_async(self, coro: Any) -> None:
		if self._event_loop is None or not self._event_loop.is_running():
			logger.warning("Dropping scheduled coroutine because the web event loop is not running")
			coro.close()
			return
		try:
			running_loop = asyncio.get_running_loop()
		except RuntimeError:
			running_loop = None
		if running_loop is self._event_loop:
			self._event_loop.create_task(coro)
		else:
			asyncio.run_coroutine_threadsafe(coro, self._event_loop)

	# --- Broadcasting ---

	async def broadcast(self, event: str, data: Any) -> None:
		"""Broadcast a message to all connected WebSocket clients that have not seen this data yet."""
		disconnected = set()
		message = custom_json_dumps({event: data})

		for websocket in self.ws_connections.keys():
			if self.ws_connections[websocket].get(event) == message:
				continue
			try:
				await websocket.send_text(message)
				self.ws_connections[websocket][event] = message
			except Exception as e:
				logger.error(f"Error sending to websocket: {e}")
				disconnected.add(websocket)

		for ws in disconnected:
			self.ws_connections.pop(ws, None)

	async def broadcast_all(self) -> None:
		await self.broadcast("branches", self.get_global_branches_to_emit())
		await self.broadcast("environments", self.get_global_envs_to_emit())

	async def broadcast_branches(self, data: Any) -> None:
		await self.broadcast("branches", data)

	async def broadcast_environments(self, data: Any) -> None:
		await self.broadcast("environments", data)

	async def broadcast_error(self, data: Any) -> None:
		await self.broadcast("error", data)

	def emit_envs(self) -> None:
		"""Sync callback used by App's processing loop to push updates to clients."""
		self._schedule_async(self.broadcast_branches(self.get_global_branches_to_emit()))
		self._schedule_async(self.broadcast_environments(self.get_global_envs_to_emit()))

	# --- Routes ---

	async def serve_index(self) -> FileResponse:
		return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))

	async def serve_state(self) -> Response:
		return Response(content=custom_json_dumps(self.get_global_envs_to_emit()), media_type="application/json")

	async def serve_branches_route(self) -> Response:
		return Response(content=custom_json_dumps(self.get_global_branches_to_emit()), media_type="application/json")

	async def serve_static(self, path: str) -> FileResponse:
		file_path = os.path.join(FRONTEND_DIR, path)
		if os.path.exists(file_path) and os.path.isfile(file_path):
			return FileResponse(file_path)
		return FileResponse(os.path.join(FRONTEND_DIR, 'index.html'))

	async def websocket_endpoint(self, websocket: WebSocket) -> None:
		await websocket.accept()
		self.ws_connections[websocket] = {}

		try:
			# Send initial state on connect and record it so duplicate broadcasts are suppressed
			branches_payload = custom_json_dumps({"branches": self.get_global_branches_to_emit()})
			envs_payload = custom_json_dumps({"environments": self.get_global_envs_to_emit()})
			await websocket.send_text(branches_payload)
			self.ws_connections[websocket]["branches"] = branches_payload
			await websocket.send_text(envs_payload)
			self.ws_connections[websocket]["environments"] = envs_payload

			while True:
				data = await websocket.receive_text()
				message = json.loads(data)

				if "update" in message:
					update_data = message.get("update") or {}
					logger.info(f"Received environment update: {update_data}")
					if self.secondaryManager:
						await self.secondaryManager.send({"update": update_data})
					id = update_data.get('id', '')
					if id == '':
						self.core.request_reset()
					elif id not in self.core.environments.keys() and id not in {j for it in self.secondaryManager or [] for j in it.environments.keys()}:
						logger.warning(f"Received update for unknown environment id {id}")
						continue
					elif id in self.core.environments.keys():
						env = self.core.environments.get(id, None)
						expected_token = update_data.get('token', '')
						if 'branches' in update_data:
							if not env:
								raise RuntimeError(f"Unknown env {update_data.get('id', '')}")
							env.state.set_branches(update_data.get('branches', []), expected_token=expected_token)
						if 'dry' in update_data:
							if not env:
								raise RuntimeError(f"Unknown env {update_data.get('id', '')}")
							env.state.set_dry(bool(update_data['dry']), expected_token)

						if env:
							self.core.request_reset()
							logger.info(f"Updated environment {env.id} branches to {update_data.get('branches')}, dry={update_data.get('dry')}")
					self.core.notify_environment_update()

					await self.broadcast_environments(self.get_global_envs_to_emit())

		except WebSocketDisconnect:
			self.ws_connections.pop(websocket, None)
		except Exception as e:
			logger.error(f"WebSocket error: {e}:{traceback.format_exc()}")
			await self.broadcast_error({'message': f'{e}:{traceback.format_exc()}'})

	# --- Run ---

	async def start_async(self) -> None:
		import uvicorn
		config = uvicorn.Config(self.app, host='0.0.0.0', port=self.port, log_level='info')
		self._server = uvicorn.Server(config)
		try:
			await self._server.serve()
		except asyncio.CancelledError:
			self._server.should_exit = True
			raise

	def start(self) -> None:
		asyncio.run(self.start_async())

	def stop(self) -> None:
		if self._server is None:
			return
		if self._event_loop is not None and self._event_loop.is_running():
			self._event_loop.call_soon_threadsafe(lambda: setattr(self._server, "should_exit", True))
		else:
			self._server.should_exit = True

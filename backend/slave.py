import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

import websockets

logger = logging.getLogger(__name__)


class SlaveConnector:
	"""Manages the WebSocket connection to a slave brencher instance."""

	def __init__(
		self,
		slave_url: str,
		on_branches: Callable[[], Awaitable[None]],
		on_environments: Callable[[], Awaitable[None]],
		on_error: Callable[[Any], Awaitable[None]],
	) -> None:
		self._slave_url = slave_url
		self.branches: Dict[str, Any] = {}
		self.environments: Dict[str, Any] = {}
		self._send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
		self._task: Optional[asyncio.Task[None]] = None
		self._on_branches = on_branches
		self._on_environments = on_environments
		self._on_error = on_error

	def start(self) -> None:
		"""Start the background task that maintains the slave WebSocket connection."""
		self._task = asyncio.create_task(self._connect())

	@property
	def is_active(self) -> bool:
		return self._task is not None and not self._task.done()

	async def send(self, msg: Dict[str, Any]) -> None:
		"""Enqueue a message to be forwarded to the slave."""
		await self._send_queue.put(msg)

	async def _connect(self) -> None:
		"""Continuously connect (and reconnect) to the slave WebSocket."""
		logger.info(f"SLAVE_BRENCHER set, will connect to slave at {self._slave_url}")

		while True:
			try:
				ws_url = (
					self._slave_url
					.replace('http://', 'ws://')
					.replace('https://', 'wss://')
					+ '/ws'
				)

				async with websockets.connect(ws_url) as ws:
					logger.info("Connected to slave WebSocket")

					async def handle_messages() -> None:
						async for msg in ws:
							parsed = json.loads(msg)
							if "branches" in parsed:
								self.branches = parsed["branches"]
								await self._on_branches()
							elif "environments" in parsed:
								self.environments = parsed["environments"]
								await self._on_environments()
							elif "error" in parsed:
								await self._on_error(parsed["error"])

					async def handle_sends() -> None:
						while True:
							msg = await self._send_queue.get()
							await ws.send(json.dumps(msg))

					await asyncio.gather(
						handle_messages(),
						handle_sends(),
					)

			except Exception as e:
				logger.error(f"Could not connect to SLAVE_BRENCHER {self._slave_url}: {e}")
				await asyncio.sleep(60)

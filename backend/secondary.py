import asyncio
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional, Iterator

import websockets

logger = logging.getLogger(__name__)


class SecondaryConnector:

	def __init__(
		self,
		url: str,
		on_branches: Callable[[], Awaitable[None]],
		on_environments: Callable[[], Awaitable[None]],
		on_error: Callable[[Any], Awaitable[None]],
	) -> None:
		self._url = url
		self.branches: Dict[str, Any] = {}
		self.environments: Dict[str, Any] = {}
		self._send_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
		self._task: Optional[asyncio.Task[None]] = None
		self._on_branches = on_branches
		self._on_environments = on_environments
		self._on_error = on_error

	def start(self) -> None:
		self._task = asyncio.create_task(self._connect())

	@property
	def is_active(self) -> bool:
		return self._task is not None and not self._task.done()

	async def send(self, msg: Dict[str, Any]) -> None:
		await self._send_queue.put(msg)

	async def _connect(self) -> None:
		logger.info(f"Connecting to secondary at {self._url}")

		while True:
			try:
				ws_url = (
					self._url
					.replace('http://', 'ws://')
					.replace('https://', 'wss://')
					+ '/ws'
				)

				async with websockets.connect(ws_url) as ws:
					logger.info(f"Connected to secondary WebSocket at {self._url}")

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
				logger.error(f"Could not connect to secondary {self._url}: {e}")
				await asyncio.sleep(60)

class SecondaryManager():
	def __init__(self,
		urls: str,
		on_branches: Callable[[], Awaitable[None]],
		on_environments: Callable[[], Awaitable[None]],
		on_error: Callable[[Any], Awaitable[None]],
	) -> None:
		self.lst = []
		urls_list = [it.strip() for it in urls.split(",") if it.strip()]
		logger.info(f"SECONDARY_BRENCHER is {urls_list}")
		for url in urls_list:
			connector = SecondaryConnector(
				url,
				on_branches=on_branches,
				on_environments=on_environments,
				on_error=on_error,
			)
			connector.start()
			self.lst.append(connector)
	
	def __iter__(self) -> Iterator[SecondaryConnector]:
		return iter(self.lst)

	async def send(self, msg: Dict[str, Any]) -> None:
		for connector in self.lst:
			await connector.send(msg)

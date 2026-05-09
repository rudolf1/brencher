import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Iterator

import websockets

logger = logging.getLogger(__name__)


class SecondaryConnector:

	def __init__(
		self,
		url: str,
		on_update: Callable[[], Awaitable[None]],
	) -> None:
		self._url = url
		self.branches: Dict[str, Any] = {}
		self.environments: Dict[str, Any] = {}
		self._task: Optional[asyncio.Task[None]] = None
		self._on_update = on_update
		self._ws: Optional[Any] = None

	def start(self) -> None:
		self._task = asyncio.create_task(self._connect())

	@property
	def is_active(self) -> bool:
		return self._task is not None and not self._task.done()

	async def send(self, msg: Dict[str, Any]) -> None:

		payload = json.dumps(msg)
		max_attempts = 3
		timeout_seconds = 10.0

		for attempt in range(1, max_attempts + 1):
			if self._ws:
				try:
					await asyncio.wait_for(self._ws.send(payload), timeout=timeout_seconds)
					return
				except Exception as e:
					logger.warning(f"Send attempt {attempt}/{max_attempts} failed for {self._url}: {e}")

			if attempt < max_attempts:
				await asyncio.sleep(timeout_seconds * attempt)

		logger.error(f"Dropping message for secondary {self._url} after {max_attempts} attempts")

	async def _connect(self) -> None:
		logger.info(f"Connecting to secondary at {self._url}")
		reconnect_delay_seconds = 5

		while True:
			try:
				ws_url = (
					self._url
					.replace('http://', 'ws://')
					.replace('https://', 'wss://')
					+ '/ws'
				)

				async with websockets.connect(
					ws_url,
					ping_interval=20,
					ping_timeout=20,
					close_timeout=5,
				) as ws:
					self._ws = ws
					logger.info(f"Connected to secondary WebSocket at {self._url}")
					reconnect_delay_seconds = 5

					async for msg in ws:
						parsed = json.loads(msg)
						if "branches" in parsed:
							self.branches = parsed["branches"]
							await self._on_update()
						elif "environments" in parsed:
							self.environments = parsed["environments"]
							await self._on_update()
						elif "error" in parsed:
							await self._on_update()


			except asyncio.CancelledError:
				raise
			except Exception:
				logger.exception(
					f"Unexpected secondary connector error for {self._url}. "
					f"Retrying in {reconnect_delay_seconds}s"
				)
			finally:
				self._ws = None

			await asyncio.sleep(reconnect_delay_seconds)
			reconnect_delay_seconds = min(reconnect_delay_seconds * 2, 60)

class SecondaryManager():
	def __init__(self,
		urls: str,
		on_update: Callable[[], Awaitable[None]],
	) -> None:
		self.lst: List[SecondaryConnector] = []
		urls_list = [it.strip() for it in urls.split(",") if it.strip()]
		logger.info(f"SECONDARY_BRENCHER is {urls_list}")
		for url in urls_list:
			connector = SecondaryConnector(
				url,
				on_update=on_update,
			)
			connector.start()
			self.lst.append(connector)
	
	def __iter__(self) -> Iterator[SecondaryConnector]:
		return iter(self.lst)

	async def send(self, msg: Dict[str, Any]) -> None:
		await asyncio.gather(*(connector.send(msg) for connector in self.lst), return_exceptions=True)

import asyncio
import sys
import types
from typing import Callable

import pytest

from enironment import Environment
import processing
from app import App


class TestAppAsyncio:
	@pytest.mark.asyncio
	async def test_run_web_async_stops_processing_when_server_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
		process_calls = 0
		emit_calls = 0
		processing_started = asyncio.Event()
		loop = asyncio.get_running_loop()
		web_app_args: dict[str, object] = {}

		def fake_process_all_jobs(environments: list[Environment], onupdate: Callable[[], None]) -> bool:
			nonlocal process_calls
			process_calls += 1
			assert environments == []
			onupdate()
			loop.call_soon_threadsafe(processing_started.set)
			return False

		class FakeWebApp:
			def __init__(self, core: App, port: int) -> None:
				web_app_args["core"] = core
				web_app_args["port"] = port

			def emit_envs(self) -> None:
				nonlocal emit_calls
				emit_calls += 1

			async def start_async(self) -> None:
				await asyncio.wait_for(processing_started.wait(), timeout=1)

		monkeypatch.setattr(processing, "process_all_jobs", fake_process_all_jobs)
		monkeypatch.setitem(sys.modules, "web", types.SimpleNamespace(WebApp=FakeWebApp))

		app = App({})

		await asyncio.wait_for(app.runWebAsync(5001), timeout=1)

		assert process_calls >= 1
		assert emit_calls >= 1
		assert web_app_args == {"core": app, "port": 5001}
		assert app.emit_callback is None

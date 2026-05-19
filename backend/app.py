import asyncio
import logging
import os
import signal
import sys
import traceback
from typing import Any, Callable, Dict, List, Optional

from discover_envs import build_environments, parse_arguments
from utils import sigchld_handler
from dotenv import load_dotenv

from enironment import Environment, wrap_in_cached, SharedStateHolder, get_step
from steps.git import GitClone
from steps.step import CachingStep

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv("local.env")
load_dotenv('/run/secrets/brencher-secrets')


class App:

	def __init__(self, environments: Dict[str, Environment]) -> None:
		self.environments: Dict[str, Environment] = {id: wrap_in_cached(e) for id, e in environments.items()}
		self.environment_update_event = asyncio.Event()
		self.environment_update_version = 0
		self.emit_callback: Optional[Callable[[], None]] = None
		self.reset_requested = False
		self.shutdown_event = asyncio.Event()
		self.web_app: Any = None

	def get_local_envs_to_emit(self) -> Dict[str, Dict[str, Any]]:
		env_dtos: Dict[str, Dict[str, Any]] = {}
		for env in self.environments.values():
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
							"is_running": True,
						})
					else:
						pipeline_state.append({
							"name": r.name,
							"status": result,
							"is_running": False,
						})
				except BaseException as e:
					stack = traceback.format_exception(type(e), e, e.__traceback__)
					pipeline_state.append({
						"name": r.name,
						"status": [str(e), stack],
						"error": True,
						"is_running": True,
					})
			env_dtos[env.id] = {'id': env.id }
			env_dtos[env.id]['pipeline'] = pipeline_state
			try:
				shared_state = env.state.progress()
				env_dtos[env.id]['branches'] = shared_state.branches
				env_dtos[env.id]['branches_token'] = shared_state.token
				env_dtos[env.id]['dry'] = shared_state.dry
			except BaseException:
				pass
		return env_dtos

	def get_local_branches_to_emit(self) -> Dict[str, Dict[str, List[Any]]]:
		branches: Dict[str, Dict[str, List[Any]]] = {}
		for k, env in self.environments.items():
			branches[k] = {}
			try:
				step = get_step(env.pipeline, GitClone)
				branches[k] = {**step.get_branches()}
			except BaseException as e:
				stack = traceback.format_exception(type(e), e, e.__traceback__)
				logger.error(f"Error fetching branches for environment {env.id}: {str(e)}\n{''.join(stack)}")

		return branches

	async def processing_loop(self) -> None:
		while not self.shutdown_event.is_set():
			import processing

			emit = self.emit_callback or (lambda: None)
			update_version = self.environment_update_version

			logger.info("Processing")
			if self.reset_requested:
				await asyncio.to_thread(processing.reset_caches, list(self.environments.values()))
				self.reset_requested = False
			has_error = await asyncio.to_thread(processing.process_all_jobs, list(self.environments.values()), emit)
			if self.shutdown_event.is_set():
				return
			# Skip the wait when a newer update arrived while the current processing pass was running.
			if self.environment_update_version != update_version:
				continue
			timeout = 5 if has_error else 60
			try:
				await asyncio.wait_for(self.environment_update_event.wait(), timeout=timeout)
			except asyncio.TimeoutError:
				pass
			self.environment_update_event.clear()

	def notify_environment_update(self) -> None:
		self.environment_update_version += 1
		self.environment_update_event.set()

	def request_reset(self) -> None:
		self.reset_requested = True

	def stop(self) -> None:
		self.shutdown_event.set()
		self.notify_environment_update()
		if self.web_app is not None:
			self.web_app.stop()

	async def runAsync(self) -> None:
		await self.processing_loop()

	async def runHeadlessAsync(self) -> None:
		await self.processing_loop()

	def runHeadless(self) -> None:
		"""Run the processing loop until cancelled; blocks forever."""
		asyncio.run(self.runHeadlessAsync())

	async def _run_web_server(self, web_app: Any) -> None:
		"""Raise a sentinel exception when the server stops so TaskGroup cancels processing."""
		await web_app.start_async()
		raise _WebServerStopped()

	async def runWebAsync(self, port: int) -> None:
		import web
		web_app = web.WebApp(core=self, port=port)
		self.web_app = web_app
		self.emit_callback = web_app.emit_envs
		try:
			# Keep processing and web serving coupled so shutdown or fatal failure tears down the whole app.
			async with asyncio.TaskGroup() as task_group:
				task_group.create_task(self.processing_loop())
				task_group.create_task(self._run_web_server(web_app))
		except* _WebServerStopped:
			pass
		finally:
			self.emit_callback = None
			self.web_app = None

	def runWeb(self, port: int) -> None:
		asyncio.run(self.runWebAsync(port))

	def run(self) -> None:
		asyncio.run(self.runAsync())


class _WebServerStopped(Exception):
	pass

if __name__ == '__main__':
	cli_env_ids_list = sys.argv[1:]
	cli_env_ids_str: str
	if len(cli_env_ids_list) == 0:
		cli_env_ids_str = os.getenv('PROFILES', '')
	else:
		cli_env_ids_str = cli_env_ids_list[0]

	signal.signal(signal.SIGCHLD, sigchld_handler)
	environments = build_environments(cli_env_ids_str)
	if 'dry' in sys.argv[1:]:
		for e in environments.values():
			e.state.set_dry(True)

	app1 = App(environments)

	if 'noweb' in sys.argv[1:]:
		app1.runHeadless()
	else:
		app1.runWeb(5001)

import logging
import os
import signal
import sys
import threading
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
		self.state_lock = threading.Lock()
		self.environment_update_event = threading.Event()
		self.emit_callback: Optional[Callable[[], None]] = None

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

	def processing_thread(self) -> None:
		while True:
			import processing

			emit = self.emit_callback or (lambda: None)

			with self.state_lock:
				logger.info(f"Processing")
				if processing.process_all_jobs(list(self.environments.values()), emit):
					self.environment_update_event.wait(timeout=1 * 5)
				else:
					self.environment_update_event.wait(timeout=1 * 60)
				self.environment_update_event.clear()

	def run(self) -> None:
		processing = threading.Thread(target=self.processing_thread)
		processing.daemon = True
		processing.start()

	def runHeadless(self) -> None:
		"""Run the processing loop on the current thread; blocks forever."""
		self.processing_thread()

	def runWeb(self, port: int) -> None:
		import web
		web_app = web.WebApp(core=self, port=port)
		self.emit_callback = web_app.emit_envs
		self.run()
		web_app.start()

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

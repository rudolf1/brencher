import logging
import os
import signal
import sys
import threading
import traceback
from typing import Any, Callable, Dict, List, Optional

from secondary import SecondaryManager
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


def build_environments(cli_env_ids_str: str, dry_run: bool = False) -> Dict[str, Environment]:
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
	environments: Dict[str, Environment] = {e.id: e for e in environments_l}

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
						for step in env.pipeline:
							resolve_step = step
							if isinstance(step, CachingStep):
								resolve_step = step._step
							if isinstance(resolve_step, SharedStateHolder):
								resolve_step.set_branches([(v, 'HEAD')])
						logger.info(f"Overriding environment {k} branches to {(v, 'HEAD')}")
					else:
						logger.warning(f"Environment {k} not found to override branches")
				else:
					logger.info(f"No branch override for environment {k}")
	if dry_run:
		for e in environments.values():
			e.state.set_dry(True)

	logger.info(f"Resulting profiles {environments.keys()}")

	return environments


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
	environments = build_environments(cli_env_ids_str, 'dry' in sys.argv[1:])
	app1 = App(environments)

	if 'noweb' in sys.argv[1:]:
		app1.runHeadless()
	else:
		app1.runWeb(5001)

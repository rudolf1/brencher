import logging
import time
from typing import List, Callable

from enironment import Environment
from steps.git import GitUnmerge, GitClone, ResolveInitialBranches
from steps.step import CachingStep

logger = logging.getLogger(__name__)

_last_reset_time: float = 0
RESET_INTERVAL = 3 * 60  # 3 minutes in seconds


def reset_caches(environemnts: List[Environment]) -> None:
	for env in environemnts:
		for step in env.pipeline:
			if isinstance(step, CachingStep):
				step.reset()


def process_all_jobs(
		environemnts: List[Environment],
		onupdate: Callable[[], None]
) -> bool:
	global _last_reset_time
	current_time = time.time()
	if current_time - _last_reset_time >= RESET_INTERVAL:
		reset_caches(environemnts)
		_last_reset_time = current_time

	has_error = False
	for env in environemnts:
		if len(env.branches) == 0:
			git_clone_step = None
			git_unmerge_step = None
			for step in env.pipeline:
				if isinstance(step, GitClone) or (isinstance(step, CachingStep) and isinstance(step.step, GitClone)):
					git_clone_step = step
				if isinstance(step, GitUnmerge) or (isinstance(step, CachingStep) and isinstance(step.step, GitUnmerge)):
					git_unmerge_step = step
				if git_clone_step is not None and git_unmerge_step is not None:
					break

			if git_clone_step is not None and git_unmerge_step is not None:
				try:
					onupdate()
					resolve_step = ResolveInitialBranches(
						wd=git_clone_step,
						unmerge=git_unmerge_step,
					)
					resolve_step.env = env
					resolve_step.progress()
				except Exception as e:
					error_msg = f"Error resolving initial branches for {env.id}: {str(e)}"
					logger.error(error_msg)
					has_error = True
					onupdate()
					continue

		for step in env.pipeline:
			try:
				onupdate()
				step.progress()
			except BaseException as e:
				error_msg = f"Error processing release {env.id}, job {step.name}: {str(e)}"
				logger.error(error_msg)
				has_error = True
			finally:
				onupdate()
	return has_error

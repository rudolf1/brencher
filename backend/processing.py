import logging
import time
from typing import List, Callable

from enironment import Environment
from steps.git import GitUnmerge
from steps.step import CachingStep

logger = logging.getLogger(__name__)

_last_reset_time: float = 0
RESET_INTERVAL = 3 * 60  # 3 minutes in seconds

def process_all_jobs(
		environemnts: List[Environment],
		onupdate: Callable[[], None]
) -> bool:
	global _last_reset_time
	current_time = time.time()
	if current_time - _last_reset_time >= RESET_INTERVAL:
		for env in environemnts:
			for step in env.pipeline:
				if isinstance(step, CachingStep):
					step.reset()
		_last_reset_time = current_time
	has_error = False
	for env in environemnts:
		for step in env.pipeline:
			try:
				step.progress()
				if isinstance(step, GitUnmerge) and len(env.branches) == 0:
					# TODO Move to separate job.
					# If branches list empty, need to find any brunch which includes commit and add pair (branch, commit)
					# If branches not empty, need to find most priority branch (project specific) and add (branch, HEAD)
					env.branches = step.progress()
					logger.info(f"Branches on startup resolved {env.id}, job {step.name}: {env.branches}")
			except BaseException as e:
				error_msg = f"Error processing release {env.id}, job {step.name}: {str(e)}"
				logger.error(error_msg, e)
				onupdate()
				has_error = True
			finally:
				onupdate()
	return has_error

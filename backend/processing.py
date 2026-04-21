import logging
import time
from typing import List, Callable

from enironment import Environment
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

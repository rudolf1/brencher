from enironment import Environment
from steps.step import CachingStep
from steps.git import GitUnmerge
from typing import List, Tuple, Callable
import logging

logger = logging.getLogger(__name__)

def process_all_jobs(
        environemnts: List[Environment],
        onupdate: Callable[[], None]
    ) -> None:
    for env in environemnts:
            for step in env.pipeline:
                try:
                    if isinstance(step, CachingStep):
                         step.reset()
                    step.progress()
                    if isinstance(step, GitUnmerge) and len(env.branches) == 0:
                        # TODO Move to separate job.
                        # If branches list empty, need to find any brunch which includes commit and add pair (branch, commit)
                        # If branches not empty, need to find most priority branch (project specific) and add (branch, HEAD)
                        env.branches= step.progress()
                        logger.error(f"Branches on startup resolved {env.id}, job {step.name}: {env.branches}")
                except BaseException as e:
                    error_msg = f"Error processing release {env.id}, job {step.name}: {str(e)}"
                    logger.error(error_msg)
                    onupdate()
                finally:
                    onupdate()




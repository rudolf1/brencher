from enironment import Environment
from steps.step import AbstractStep
from steps.git import GitUnmerge
from typing import List, Tuple, Callable
import logging

logger = logging.getLogger(__name__)

def process_all_jobs(
        environemnts: List[Tuple[Environment, List[AbstractStep]]],
        onupdate: Callable[[], None]
    ) -> None:
    for env, pipe in environemnts:
            for step in pipe:
                try:
                    step._result = None
                    step.result
                    if isinstance(step, GitUnmerge) and len(env.branches) == 0:
                        # TODO Move to separate job.
                        # If branches list empty, need to find any brunch which includes commit and add pair (branch, commit)
                        # If branches not empty, need to find most priority branch (project specific) and add (branch, HEAD)
                        result = step.result
                        if result and isinstance(result[0], tuple):
                            env.branches = [ (b1, c) for c, b in result for b1 in b ]
                        logger.error(f"Branches on startup resolved {env.id}, job {step.name}: {env.branches}")
                except BaseException as e:
                    error_msg = f"Error processing release {env.id}, job {step.name}: {str(e)}"
                    logger.error(error_msg)
                    onupdate()
                finally:
                    onupdate()




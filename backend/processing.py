from enironment import Environment
from steps.step import AbstractStep
from typing import List, Dict, Any, Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)

def process_all_jobs(
        environemnts: List[Tuple[Environment, List[AbstractStep]]], 
        onupdate: Callable[[], None]
    ):
    for env, pipe in environemnts:
            for step in pipe:
                try:
                    step.result
                except BaseException as e:
                    error_msg = f"Error processing release {env.id}, job {step.name}: {str(e)}"
                    logger.error(error_msg)
                    onupdate()
                finally:
                    onupdate()
        



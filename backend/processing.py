from enironment import Environment
from steps.step import AbstractStep
from typing import List, Dict, Any, Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)

def do_job(
        environemnts: List[Tuple[Environment, List[AbstractStep]]], 
        onupdate: Callable[[], None]
    ):
    for env, pipe in environemnts:
        try:
            if env.state != 'Active':
                continue
            for step in pipe:
                step.do_job()
                onupdate()
        
        except BaseException as e:
            error_msg = f"Error processing release {env.id}: {str(e)}"
            logger.error(error_msg)
            onupdate()


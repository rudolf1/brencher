import logging
from typing import Any
from steps.step import AbstractStep
from enironment import Environment
import requests

logger = logging.getLogger(__name__)

class UrlCheck(AbstractStep[str]):
    
    def __init__(self, env: Environment, url: str, expected: Any, **kwargs): # type: ignore[no-untyped-def]
        super().__init__(env=env, **kwargs)
        self.url = url
        self.expected = expected

    def progress(self) -> str:
        logger.info(f"Checking {self.url}")
        result = requests.get(self.url)
        if result.status_code != 200:
            raise Exception(f"URL check failed: status code {result.status_code}")
        json_result = result.json()


        def compare_nested(expected: Any, actual: Any, path: str = "") -> None:
            if isinstance(expected, dict):
                if not isinstance(actual, dict):
                    raise Exception(f"URL check failed at {path}: expected dict, got {type(actual).__name__}")
                for key, value in expected.items():
                    new_path = f"{path}.{key}" if path else key
                    if key not in actual:
                        raise Exception(f"URL check failed: missing key '{new_path}'")
                    compare_nested(value, actual[key], new_path)
            elif isinstance(expected, list):
                if not isinstance(actual, list):
                    raise Exception(f"URL check failed at {path}: expected list, got {type(actual).__name__}")
                if len(expected) != len(actual):
                    raise Exception(f"URL check failed at {path}: expected list length {len(expected)}, got {len(actual)}")
                for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                    compare_nested(exp_item, act_item, f"{path}[{i}]")
            else:
                if expected != actual:
                    raise Exception(f"URL check failed at {path}: expected {expected}, got {actual}")
        if isinstance(self.expected, dict):
            compare_nested(self.expected, json_result)
        elif callable(self.expected):
            self.expected(json_result)
        return "Ok"
    
class SimpleLog(AbstractStep[Any]):
    def __init__(self, env: Environment, message: Any, **kwargs):# type: ignore[no-untyped-def]
        super().__init__(env=env, **kwargs)
        self.message = message
        
    def progress(self) -> Any:
        return self.message
    

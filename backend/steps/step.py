from abc import ABC, abstractmethod
from typing import List, Optional, Union, Tuple, Any
from typing import TypeVar, Generic
from dataclasses import dataclass, asdict, field
from enironment import Environment
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')
class AbstractStep(ABC, Generic[T]):

    env: Environment
    name: str
    _result: T | BaseException = BaseException("No result yet")

    def __init__(self, env: Environment, n: str | None = None) -> None:
        if n is None:
            n = self.__class__.__name__
        self.name = n
        self.env = env

    @property
    def result_obj(self) -> Union[T, BaseException]:
        return self._result

    @property
    def result(self) -> T:
        if isinstance(self._result, BaseException):
            raise self._result
        return self._result

    def do_job(self):
        try:
            self._result = self.progress()
        except Exception as e:
            logger.error(f"Job failed: {e}")
            self._result = e

    @abstractmethod
    def progress(self) -> T | BaseException:
        pass

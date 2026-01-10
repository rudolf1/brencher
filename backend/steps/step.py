from abc import ABC, abstractmethod
from typing import List, Optional, Union, Tuple, Any
from typing import TypeVar, Generic
from dataclasses import dataclass, asdict, field
from enironment import Environment
import logging

logger = logging.getLogger(__name__)

class NotReadyException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

T = TypeVar('T')
class AbstractStep(ABC, Generic[T]):

    env: Environment
    name: str
    _result: T | BaseException | None

    def __init__(self, env: Environment, n: str | None = None) -> None:
        if n is None:
            n = self.__class__.__name__
        self.name = n
        self._result = NotReadyException(f"No result yet for {self.name}")
        self.env = env

    @property
    def result_obj(self) -> Union[T, BaseException | None]:
        return self._result

    @property
    def result(self) -> T:
        if self._result is None or isinstance(self._result, NotReadyException):
            try:
                self._result = self.progress()
            except BaseException as e:
                self._result = e

        if isinstance(self._result, BaseException):
            raise self._result
        return self._result

    @abstractmethod
    def progress(self) -> T:
        pass

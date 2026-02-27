from abc import ABC, abstractmethod
from typing import Union
from typing import TypeVar, Generic
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
    def __init__(self, env: Environment, n: str | None = None) -> None:
        if n is None:
            n = self.__class__.__name__
        self.name = n
        self.env = env

    @abstractmethod
    def progress(self) -> T:
        pass

class CachingStep(AbstractStep[T], Generic[T]):

    _result: T | BaseException

    def __init__(self, step: AbstractStep[T]) -> None:
        self.step = step
        self._result = NotReadyException(f"No result yet for {self.step.name}")
       

    def progress(self) -> T:
        if self._result is None or isinstance(self._result, NotReadyException):
            try:
                self._result = self.step.progress()
            except BaseException as e:
                self._result = e

        if isinstance(self._result, BaseException):
            raise self._result
        else:
            return self._result

    def reset(self) -> None:
        self._result = NotReadyException(f"No result yet for {self.step.name}")

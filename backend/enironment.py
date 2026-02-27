from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Union
from typing import TypeVar, Generic
import logging
from dataclasses import dataclass
from typing import List, Tuple
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)



T = TypeVar('T')


@dataclass
class Environment:
    id: str
    branches: List[Tuple[str, str]]  # List of [branch_name, desired_commit] pairs
    dry: bool
    repo: str # git repo
    pipeline: List[AbstractStep]

    def __post_init__(self) -> None:
        for p in self.pipeline:
            p.env = self

class AbstractStep(ABC, Generic[T]):

    _env: Environment | None = None
    
    name: str
    def __init__(self, n: str | None = None) -> None:
        if n is None:
            n = self.__class__.__name__
        self.name = n

    @property
    def env(self) -> Environment:
        if self._env is None:
            raise BaseException(f"Environment not set for {self.name}")
        return self._env

    @env.setter
    def env(self, value: Environment) -> None:
        if value is None:
            raise BaseException(f"Environment not set for {self.name}")
        self._env = value

    @abstractmethod
    def progress(self) -> T:
        pass

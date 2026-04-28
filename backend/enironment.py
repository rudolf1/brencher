from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, runtime_checkable, Protocol, Tuple, TypeAlias, Any
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Environment:
	id: str
	state: SharedStateHolder
	repo: str  # git repo
	pipeline: List[AbstractStep]

	def __post_init__(self) -> None:
		for p in self.pipeline:
			p.env = self

	@property
	def dry(self) -> bool:
		"""Get the dry run state from the shared state."""
		return self.state.progress().dry



@dataclass
class SharedState:
	branches: List[Tuple[str, str]]
	dry: bool
	token: str | None = None


class SharedStateConflictError(BaseException):
	def __init__(self, message: str) -> None:
		super().__init__(message)

@runtime_checkable
class SharedStateHolder(Protocol):
	def set_branches(self, branches: List[Tuple[str, str]], expected_token: str | None = None) -> SharedState:
		pass

	def set_dry(self, dry: bool, expected_token: str | None = None) -> SharedState:
		pass

	def progress(self) -> SharedState:
		pass



class AbstractStep[T](ABC):
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


def wrap_in_cached(e: Environment) -> Environment:
	from dataclasses import replace
	from steps.step import CachingStep
	result = replace(e, pipeline=[CachingStep(step) for step in e.pipeline])
	cached = {it._step: it for it in result.pipeline if isinstance(it, CachingStep)}
	for step in result.pipeline:
		if isinstance(step, CachingStep):
			step._step.env = result
			for attr_name in dir(step._step):
				if not attr_name.startswith('_'):
					attr_value = getattr(step._step, attr_name)
					if isinstance(attr_value, AbstractStep):
						cached_step = cached.get(attr_value)
						if cached_step:
							setattr(step._step, attr_name, cached_step)

	return result


def get_step(env: List[AbstractStep[Any]], class_or_tuple: type[T]) -> T:
	from steps.step import CachingStep
	for step in env:
		if isinstance(step, class_or_tuple) or (isinstance(step, CachingStep) and isinstance(step._step, class_or_tuple)):
			return step  # type: ignore[return-value]
	raise BaseException(f"Not step found {class_or_tuple}")
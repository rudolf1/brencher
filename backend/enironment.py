from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class Environment:
	id: str
	branches: List[Tuple[str, str]]  # List of [branch_name, desired_commit] pairs
	dry: bool
	repo: str  # git repo
	pipeline: List[AbstractStep]

	def __post_init__(self) -> None:
		for p in self.pipeline:
			p.env = self


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
	cached = {it.step: it for it in result.pipeline if isinstance(it, CachingStep) }
	for step in result.pipeline:
		if isinstance(step, CachingStep):
			step.step.env = result
			for attr_name in dir(step.step):
				if not attr_name.startswith('_'):
					attr_value = getattr(step.step, attr_name)
					if isinstance(attr_value, AbstractStep):
						cached_step = cached.get(attr_value)
						if cached_step:
							setattr(step.step, attr_name, cached_step)

	return result


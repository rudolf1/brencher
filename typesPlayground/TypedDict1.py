import abc
from abc import ABC
from dataclasses import dataclass
from typing import TypedDict, List, runtime_checkable, TypeVar, Sequence

T = TypeVar('T')  # Can be anything


@runtime_checkable
class C1(TypedDict):
	version: str


@runtime_checkable
class C2(TypedDict):
	version1: str


@dataclass
class C1V(C1, C2):
	name: str


# version: str
# version1: str


class AbstractCallable[T](ABC):
	@abc.abstractmethod
	def progress(self) -> T | None:
		pass


# T1 = TypeVar("T1", bound=C1)
def x1(d: AbstractCallable[Sequence[C1]]) -> None:
	pass


# T2 = TypeVar("T2", bound=C2)
def x2(d: AbstractCallable[Sequence[C2]]) -> None:
	pass


class MockCallable(AbstractCallable[List[C1V]]):
	def progress(self) -> List[C1V] | None:
		return [C1V(name="service1", version="1.0", version1="1.0")]


mock_callable: AbstractCallable[List[C1V]] = MockCallable()
x1(mock_callable)
x2(mock_callable)

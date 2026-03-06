import abc
from abc import abstractmethod, ABC
from typing import Dict, TypedDict, List, runtime_checkable, Protocol, Callable, Generic, TypeVar, Sequence
from dataclasses import dataclass

T = TypeVar('T')  # Can be anything

@runtime_checkable
class C1(Protocol):
	version: str
@runtime_checkable
class C2(Protocol):
	version1: str

@dataclass
class C1V(C1,C2):
	name: str
	version: str
	version1: str

@runtime_checkable
class Coll[T](Protocol):
	v: T

class AbstractCallable[T](ABC):
	@abc.abstractmethod
	def progress(self) -> T | None:
		pass

def x1(d: AbstractCallable[Sequence[C1]]) -> None:
	pass
def x2(d: AbstractCallable[Sequence[C2]]) -> None:
	pass

class MockCallable(AbstractCallable[List[C1V]]):
	def progress(self) -> List[C1V] | None:
		return [C1V(name="service1", version="1.0", version1="1.0")]


mock_callable = MockCallable()
x1(mock_callable)
x2(mock_callable)

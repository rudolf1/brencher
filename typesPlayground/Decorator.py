from functools import wraps
from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")


def info(func: Callable[P, R]) -> Callable[P, R]:
	@wraps(func)
	def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
		print(func.__name__)
		print(func.__doc__)
		return func(*args, **kwargs)

	return wrapper


def info_pep695[**P, R](func: Callable[P, R]) -> Callable[P, R]:
	@wraps(func)
	def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
		print(func.__name__)
		print(func.__doc__)
		return func(*args, **kwargs)

	return wrapper


@info
def greet(name: str, greeting: str = "Hello") -> str:
	"""Greet someone."""
	return f"{greeting}, {name}!"


@info_pep695
def add(a: int, b: int) -> int:
	"""Add two numbers."""
	return a + b


result1 = greet("Alice")
result2 = greet("Bob", greeting="Hi")
result3 = add(1, 2)

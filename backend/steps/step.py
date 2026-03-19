from typing import TypeVar, Generic

from enironment import AbstractStep

T = TypeVar('T')


class NotReadyException(BaseException):
	def __init__(self, message: str):
		super().__init__(message)


class CachingStep(AbstractStep[T], Generic[T]):
	_result: T | BaseException
	reset_cache: bool = False

	def __init__(self, step: AbstractStep[T]) -> None:
		super().__init__(n=step.name)
		self.step = step
		self._result = NotReadyException(f"No result yet for {self.step.name}")

	def progress(self) -> T:
		if self.reset_cache or self._result is None or isinstance(self._result, BaseException):
			try:
				self._result = self.step.progress()
			except BaseException as e:
				self._result = e
		self.reset_cache = False
		if isinstance(self._result, BaseException):
			raise self._result from None
		else:
			return self._result

	def reset(self) -> None:
		self.reset_cache = True

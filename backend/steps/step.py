import hashlib
import json
from typing import TypeVar, Generic, Any

from enironment import AbstractStep

T = TypeVar('T')


class NotReadyException(BaseException):
	def __init__(self, message: str):
		super().__init__(message)


def _stable_hash(obj: Any) -> str:
	"""Compute a stable SHA-256 hash of an object via JSON serialization."""
	try:
		serialized = json.dumps(obj, sort_keys=True, default=repr)
	except Exception:
		serialized = repr(obj)
	return hashlib.sha256(serialized.encode()).hexdigest()


class CachingStep(AbstractStep[T], Generic[T]):
	_result: T | BaseException
	_input_hash: str | None

	def __init__(self, step: AbstractStep[T]) -> None:
		super().__init__(n=step.name)
		self._step = step
		self._result = NotReadyException(f"No result yet for {self._step.name}")
		self._input_hash = None

	def _compute_input_hash(self) -> str:
		"""Compute a stable hash of all AbstractStep dependency outputs."""
		inputs: dict[str, Any] = {}
		for attr_name, attr_value in vars(self._step).items():
			if isinstance(attr_value, AbstractStep):
				try:
					inputs[attr_name] = attr_value.progress()
				except BaseException as e:
					inputs[attr_name] = repr(e)
		return _stable_hash(inputs)

	def progress(self) -> T:
		current_hash = self._compute_input_hash()
		if self._input_hash != current_hash or isinstance(self._result, BaseException):
			try:
				self._result = self._step.progress()
			except BaseException as e:
				self._result = e
			self._input_hash = current_hash
		if isinstance(self._result, BaseException):
			raise self._result from None
		return self._result

	def reset(self) -> None:
		self._input_hash = None

	def __getattr__(self, name: str) -> Any:
		"""Delegate unknown attributes to the wrapped step."""
		return getattr(self._step, name)

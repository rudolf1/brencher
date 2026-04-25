"""
Unit tests for CachingStep input-hash-based cache invalidation.
"""
from typing import Any

import pytest

from enironment import AbstractStep, Environment
from steps.shared_state import SharedStateHolderInMemory
from steps.step import CachingStep, NotReadyException


class ConstantStep(AbstractStep[str]):
	"""Step that always returns a fixed value, counting calls."""

	def __init__(self, value: str) -> None:
		super().__init__()
		self.value = value
		self.call_count = 0

	def progress(self) -> str:
		self.call_count += 1
		return self.value


class DependentStep(AbstractStep[str]):
	"""Step that depends on another AbstractStep and appends a suffix."""

	def __init__(self, upstream: AbstractStep[str], suffix: str = "-processed") -> None:
		super().__init__()
		self.upstream = upstream
		self.suffix = suffix
		self.call_count = 0

	def progress(self) -> str:
		self.call_count += 1
		return self.upstream.progress() + self.suffix


class FailingStep(AbstractStep[str]):
	"""Step that always raises an exception."""

	def __init__(self) -> None:
		super().__init__()
		self.call_count = 0

	def progress(self) -> str:
		self.call_count += 1
		raise RuntimeError("step failed")


def _make_env(steps: list[AbstractStep[Any]]) -> Environment:
	return Environment(id="test", state=SharedStateHolderInMemory(unmerge=None), repo="repo", pipeline=steps)


class TestCachingStep:
	def test_executes_on_first_call(self) -> None:
		inner = ConstantStep("hello")
		cached = CachingStep(inner)
		_make_env([cached])

		result = cached.progress()

		assert result == "hello"
		assert inner.call_count == 1

	def test_caches_result_when_inputs_unchanged(self) -> None:
		inner = ConstantStep("hello")
		cached = CachingStep(inner)
		_make_env([cached])

		cached.progress()
		cached.progress()
		cached.progress()

		assert inner.call_count == 1

	def test_reexecutes_when_upstream_output_changes(self) -> None:
		upstream = ConstantStep("v1")
		inner = DependentStep(upstream)
		cached_upstream = CachingStep(upstream)
		cached = CachingStep(inner)
		_make_env([cached_upstream, cached])

		# Wire up: replace inner's `upstream` reference with the cached wrapper
		inner.upstream = cached_upstream

		result1 = cached.progress()
		assert result1 == "v1-processed"
		assert inner.call_count == 1

		# Change the upstream value so the hash changes
		upstream.value = "v2"
		# Force the upstream cache to re-execute so it returns the new value
		cached_upstream.reset()

		result2 = cached.progress()
		assert result2 == "v2-processed"
		assert inner.call_count == 2

	def test_does_not_reexecute_when_upstream_output_unchanged(self) -> None:
		upstream = ConstantStep("stable")
		inner = DependentStep(upstream)
		cached_upstream = CachingStep(upstream)
		cached = CachingStep(inner)
		_make_env([cached_upstream, cached])

		inner.upstream = cached_upstream

		cached.progress()
		cached.progress()
		cached.progress()

		assert inner.call_count == 1

	def test_reset_forces_reexecution(self) -> None:
		inner = ConstantStep("hello")
		cached = CachingStep(inner)
		_make_env([cached])

		cached.progress()
		assert inner.call_count == 1

		cached.reset()
		cached.progress()
		assert inner.call_count == 2

	def test_retries_after_exception(self) -> None:
		inner = FailingStep()
		cached = CachingStep(inner)
		_make_env([cached])

		with pytest.raises(RuntimeError):
			cached.progress()
		assert inner.call_count == 1

		# Second call should retry because the result is still an exception
		with pytest.raises(RuntimeError):
			cached.progress()
		assert inner.call_count == 2

	def test_initial_state_raises_not_ready(self) -> None:
		inner = ConstantStep("hello")
		cached = CachingStep(inner)
		# Do NOT set up env – but CachingStep itself should start with NotReadyException
		assert isinstance(cached._result, NotReadyException)

	def test_leaf_step_executes_once(self) -> None:
		"""A step with no AbstractStep dependencies uses a constant hash; executes only once."""
		inner = ConstantStep("leaf")
		cached = CachingStep(inner)
		_make_env([cached])

		cached.progress()
		cached.progress()

		assert inner.call_count == 1

	def test_reset_clears_hash(self) -> None:
		inner = ConstantStep("x")
		cached = CachingStep(inner)
		_make_env([cached])

		cached.progress()
		assert cached._input_hash is not None

		cached.reset()
		assert cached._input_hash is None

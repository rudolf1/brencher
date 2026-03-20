"""
Pytest configuration and shared fixtures for integration tests.

This file configures the Python path to allow importing backend modules
and provides shared fixtures for all tests.
"""
from typing import Generator, Callable, Protocol

import pytest

from tests.test_remote_repo import RemoteRepoHelper


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]) -> object:
	"""Expose test phase reports on the test item for fixture finalizers."""
	outcome = yield
	report = outcome.get_result()  # type: ignore[attr-defined]
	setattr(item, f"rep_{report.when}", report)


import time
import pytest


class EventuallyFn(Protocol):
	def __call__(
			self,
			assert_fn: Callable[[], bool],
			timeout: float = 2.0,
			interval: float = 0.05,
	) -> None: ...


@pytest.fixture
def eventually() -> EventuallyFn:
	def _eventually(assert_fn: Callable[[], bool], timeout: float = 2.0, interval: float = 0.05) -> None:
		deadline = time.monotonic() + timeout
		last_error = None
		while time.monotonic() < deadline:
			try:
				res = assert_fn()
				if res:
					return
			except AssertionError as err:
				last_error = err
				time.sleep(interval)

		raise AssertionError(f"Condition not met within {timeout:.2f}s") from last_error

	return _eventually


@pytest.fixture
def repo_helper(request: pytest.FixtureRequest) -> Generator[RemoteRepoHelper, None, None]:
	helper = RemoteRepoHelper()

	yield helper

	report = getattr(request.node, "rep_call", None)
	if report is not None and report.failed:
		helper.print_git_logs()
	helper.teardown()

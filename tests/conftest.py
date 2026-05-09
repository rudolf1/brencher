"""
Pytest configuration and shared fixtures for integration tests.

This file configures the Python path to allow importing backend modules
and provides shared fixtures for all tests.
"""
from typing import Any, Generator, Callable, Protocol, TypeVar

import pytest
import requests

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
			assert_fn: Callable[[], None],
			timeout: float = 5.0,
			interval: float = 0.5,
	) -> None: ...

T = TypeVar('T')

def assert_equal(a: T, b:T, message: str) -> None:
    if a != b:
        raise AssertionError(f"{message}: {a} != {b}")
    
def _check_state(url: str, predicate: Callable[[Any], None]) -> None:
    response = requests.get(f"{url}/state", timeout=5)
    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    state_data = response.json()
    try:
        predicate(state_data)
    except Exception as e:
        raise AssertionError(f"Predicate check failed with error: {e}\nState data: {state_data}") from e

@pytest.fixture
def eventually() -> EventuallyFn:
	def _eventually(assert_fn: Callable[[], None], timeout: float = 5.0, interval: float = 0.5) -> None:
		deadline = time.monotonic() + timeout
		last_error: BaseException | None = None
		while time.monotonic() < deadline:
			try:
				assert_fn()
				return
			except Exception as err:
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

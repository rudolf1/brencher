"""
Pytest configuration and shared fixtures for integration tests.

This file configures the Python path to allow importing backend modules
and provides shared fixtures for all tests.
"""
import sys
from pathlib import Path
from typing import Generator

import pytest

from tests.test_remote_repo import RemoteRepoHelper

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
	sys.path.insert(0, str(backend_path))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[object]) -> object:
	"""Expose test phase reports on the test item for fixture finalizers."""
	outcome = yield
	report = outcome.get_result()  # type: ignore[attr-defined]
	setattr(item, f"rep_{report.when}", report)


import time
import pytest


@pytest.fixture
def eventually():
	def _eventually(assert_fn, timeout=2.0, interval=0.05):
		deadline = time.monotonic() + timeout
		last_error = None

		while time.monotonic() < deadline:
			try:
				assert_fn()
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

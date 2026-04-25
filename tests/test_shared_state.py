"""
Unit tests for SharedState token-based optimistic locking on Environment.branches.
"""
import uuid

import pytest

from enironment import Environment, SharedState


def _make_env(branches=None) -> Environment:
	return Environment(
		id="test",
		branches=branches or [],
		dry=True,
		repo="repo",
		pipeline=[],
	)


class TestSharedState:
	def test_shared_state_has_token(self) -> None:
		state = SharedState()
		assert isinstance(state.token, str)
		assert len(state.token) > 0

	def test_shared_state_tokens_are_unique(self) -> None:
		a = SharedState()
		b = SharedState()
		assert a.token != b.token


class TestEnvironmentToken:
	def test_environment_has_token_by_default(self) -> None:
		env = _make_env()
		assert isinstance(env.token, str)
		assert len(env.token) > 0

	def test_each_environment_gets_unique_token(self) -> None:
		env1 = _make_env()
		env2 = _make_env()
		assert env1.token != env2.token

	def test_compare_and_set_succeeds_with_correct_token(self) -> None:
		env = _make_env([("main", "HEAD")])
		original_token = env.token

		result = env.compare_and_set_branches(original_token, [("main", "HEAD"), ("feature", "HEAD")])

		assert result is True
		assert env.branches == [("main", "HEAD"), ("feature", "HEAD")]

	def test_compare_and_set_refreshes_token_on_success(self) -> None:
		env = _make_env()
		original_token = env.token

		env.compare_and_set_branches(original_token, [("main", "HEAD")])

		assert env.token != original_token

	def test_compare_and_set_fails_with_wrong_token(self) -> None:
		env = _make_env([("main", "HEAD")])
		original_branches = env.branches[:]

		result = env.compare_and_set_branches("wrong-token", [("other", "HEAD")])

		assert result is False
		assert env.branches == original_branches

	def test_compare_and_set_does_not_change_token_on_failure(self) -> None:
		env = _make_env()
		original_token = env.token

		env.compare_and_set_branches("wrong-token", [("main", "HEAD")])

		assert env.token == original_token

	def test_set_branches_updates_unconditionally(self) -> None:
		env = _make_env([("main", "HEAD")])
		original_token = env.token

		env.set_branches([("main", "HEAD"), ("feature", "HEAD")])

		assert env.branches == [("main", "HEAD"), ("feature", "HEAD")]
		assert env.token != original_token

	def test_set_branches_always_refreshes_token(self) -> None:
		env = _make_env()
		tokens = set()
		tokens.add(env.token)

		for i in range(5):
			env.set_branches([("branch" + str(i), "HEAD")])
			tokens.add(env.token)

		# Every set_branches call must produce a new distinct token.
		assert len(tokens) == 6

	def test_stale_token_rejected_after_concurrent_set_branches(self) -> None:
		env = _make_env([("main", "HEAD")])
		stale_token = env.token

		# Simulates a concurrent authoritative update (e.g. from the processing thread)
		env.set_branches([("main", "HEAD"), ("hotfix", "HEAD")])

		# UI tries to apply its change using the stale token – must be rejected
		result = env.compare_and_set_branches(stale_token, [("feature", "HEAD")])

		assert result is False
		# Branches remain as set by the authoritative update
		assert env.branches == [("main", "HEAD"), ("hotfix", "HEAD")]

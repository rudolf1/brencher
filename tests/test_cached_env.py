import pytest
from enironment import wrap_in_cached, SharedStateConflictError

from tests.test_remote_repo import RemoteRepoHelper


class TestCachedEnv:
	"""Tests for the CachedEnv wrapper around GitEnv."""

	def test_checkout_merged_empty_branches(self, repo_helper: RemoteRepoHelper) -> None:
		"""Test CheckoutMerged with empty branches list - should fail"""

		commit1 = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1",
		                                    "Initial commit")

		repo_helper.env = wrap_in_cached(repo_helper.env)

		repo_helper.set_desired_branches([])

		with pytest.raises(BaseException, match="Empty branches set"):
			repo_helper.checkout_merged.progress()

		repo_helper.set_desired_branches([('master', 'HEAD')])
		result = repo_helper.checkout_merged.progress()

		# Verify same auto branch is used with actual value checks
		assert result.commit_hash == commit1.hexsha, f"Expected {commit1.hexsha}, got {result.commit_hash}"

	def test_inmemory_state_rejects_stale_token(self, repo_helper: RemoteRepoHelper) -> None:
		_ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
		_ = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2", "Branch1 commit")

		initial_state = repo_helper.resolve_initial_branches.progress()
		initial_token = initial_state.token
		assert isinstance(initial_token, str)

		repo_helper.resolve_initial_branches.set_branches([("master", "HEAD")], expected_token=initial_token)

		with pytest.raises(SharedStateConflictError, match="State token mismatch"):
			repo_helper.resolve_initial_branches.set_branches([("branch1", "HEAD")], expected_token=initial_token)

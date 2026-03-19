import os
from typing import Generator

from flask import request
import git
import pytest

from enironment import wrap_in_cached
from steps.git import CheckoutAndMergeResult
from tests.test_remote_repo import RemoteRepoHelper


class TestCachedEnv:
    """Tests for the CachedEnv wrapper around GitEnv."""
    
    @pytest.fixture
    def repo_helper(self, request: pytest.FixtureRequest) -> Generator[RemoteRepoHelper, None, None]:
        helper = RemoteRepoHelper()

        yield helper

        report = getattr(request.node, "rep_call", None)
        if report is not None and report.failed:
            helper.print_git_logs()
        helper.teardown()


    def test_checkout_merged_empty_branches(self, repo_helper: RemoteRepoHelper) -> None:
        """Test CheckoutMerged with empty branches list - should fail"""

        commit1 = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")

        repo_helper.env = wrap_in_cached(repo_helper.env)

        repo_helper.env.branches = []

        with pytest.raises(BaseException, match="Empty branches set"):
            repo_helper.checkout_merged.progress()

        repo_helper.env.branches = [('master', 'HEAD')]
        result = repo_helper.checkout_merged.progress()

        # Verify same auto branch is used with actual value checks
        assert result.commit_hash == commit1.hexsha, f"Expected {commit1.hexsha}, got {result.commit_hash}"



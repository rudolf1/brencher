from git import BadName
import pytest

from enironment import get_step
from steps.git import CheckoutMerged
from tests.conftest import repo_helper

from .test_remote_repo import RemoteRepoHelper


class TestGitRemoveBranch:
    """Integration tests for git operations"""

    def test_checkout_merged_one_branch(self, repo_helper: RemoteRepoHelper) -> None:
        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1",
                                            "Initial commit")  # noqa: F841
        commit2 = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2",
                                            "Branch1 commit")  # noqa: F841
        commit3 = repo_helper.create_commit(repo_helper.repo, "master", "branch2", "file3.txt", "content3",
                                            "Branch2 commit")  # noqa: F841

        repo_helper.enable_caching()

        repo_helper.set_desired_branches([("branch1", "HEAD"), ("branch2", "HEAD")])
        repo_helper.progress()

        repo_helper.verify_working_directory_files([
            ('file1.txt', 'content1'),
            ('file2.txt', 'content2'),
            ('file3.txt', 'content3'),
        ])

        assert repo_helper.checkout_merged.progress().version == '-'.join([it[:8] for it in sorted([commit2.hexsha, commit3.hexsha])])

        repo_helper.remove_branch(repo_helper.repo, "branch2")

        # CheckoutMerged should raise an error when it can't find the branch, and ignore_missing_branches is False
        get_step(repo_helper.env.pipeline, CheckoutMerged).ignore_missing_branches = False

        with pytest.raises(BadName, match="Ref 'origin/branch2' did not resolve to an object"):
            repo_helper.progress()
        assert repo_helper.get_desired_branches() == [("branch1", "HEAD"), ("branch2", "HEAD")]
        with pytest.raises(BadName, match="Ref 'origin/branch2' did not resolve to an object"):
            repo_helper.checkout_merged.progress()

        # Now set ignore_missing_branches to True and verify that it ignores the missing branch and continues processing
        get_step(repo_helper.env.pipeline, CheckoutMerged).ignore_missing_branches = True
        repo_helper.progress()
        assert repo_helper.get_desired_branches() == [("branch1", "HEAD"), ("branch2", "HEAD")]
        assert repo_helper.checkout_merged.progress().version == '-'.join([it[:8] for it in [commit2.hexsha]])

        # Removing missing branch should be processed well
        repo_helper.set_desired_branches([("branch1", "HEAD")])
        repo_helper.progress()
        assert repo_helper.checkout_merged.progress().version == '-'.join([it[:8] for it in [commit2.hexsha]])

        repo_helper.verify_working_directory_files([
            ('file1.txt', 'content1'),
            ('file2.txt', 'content2'),
        ])

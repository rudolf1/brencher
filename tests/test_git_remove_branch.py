import pytest

from enironment import wrap_in_cached
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

		repo_helper.env = wrap_in_cached(repo_helper.env)
		repo_helper.env.branches = [("branch1", "HEAD"), ("branch2", "HEAD")]
		repo_helper.progress()

		repo_helper.verify_working_directory_files([
			('file1.txt', 'content1'),
			('file2.txt', 'content2'),
			('file3.txt', 'content3'),
		])

		repo_helper.remove_branch(repo_helper.repo, "branch2")
		with pytest.raises(Exception): # TODO , match="Ref 'origin/branch2' did not resolve to an object"
			repo_helper.progress()


		repo_helper.env.branches = [("branch1", "HEAD")]
		repo_helper.progress()

		repo_helper.verify_working_directory_files([
			('file1.txt', 'content1'),
			('file2.txt', 'content2'),
		])


if __name__ == "__main__":
	pytest.main([__file__, "-v"])

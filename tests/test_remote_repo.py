"""
Helper classes and utilities for git integration tests.

This module provides reusable test fixtures and mock objects for testing
git operations in an isolated environment.
"""
import os
import shutil
import tempfile
from typing import Dict, Tuple, List, Callable

import git

from enironment import Environment, AbstractStep
from steps.docker import DockerSwarmCheckResult
from steps.git import CheckoutAndMergeResult, CheckoutMerged, GitUnmerge, GitClone, HasVersion
from steps.step import CachingStep  # noqa: F401


class MockDockerSwarmCheck(AbstractStep[Dict[str, HasVersion]]):
	"""Mock DockerSwarmCheck object for testing"""

	def __init__(self, version: Callable[[], str]) -> None:
		super().__init__()
		self.version = version
		self.stack_name = "test_stack"

	def progress(self) -> Dict[str, HasVersion]:
		return {
			"service1": DockerSwarmCheckResult(
				name="service1",
				version=self.version(),
				image="test:latest",
				stack="test-stack"
			)
		}


class RemoteRepoHelper:
	"""Helper class for creating and managing test git repositories"""
	env: Environment

	def __init__(self) -> None:
		self.remote_dir = tempfile.mkdtemp(prefix="test_remote_")
		self.local_dir = tempfile.mkdtemp(prefix="test_local_")
		self.repo = git.Repo.init(self.remote_dir, bare=False)
		# Configure git user
		with self.repo.config_writer() as cw:
			cw.set_value("user", "email", "test@example.com")
			cw.set_value("user", "name", "Test User")
		git_clone = GitClone(repo_path=self.local_dir)
		checkout_merged = CheckoutMerged(
			wd=git_clone,
			git_user_email="test@example.com",
			git_user_name="Test User",
			push=False,
		)
		mock_check = MockDockerSwarmCheck(lambda: f"auto-{self.checkout_merged.progress().version}")
		git_unmerge = GitUnmerge(
			wd=git_clone,
			check=mock_check,
		)
		self.env = Environment(
			id="test1",
			branches=[],
			dry=False,
			repo=self.remote_dir,
			pipeline=[
				git_clone,
				checkout_merged,
				mock_check,
				git_unmerge
			]
		)
	@property
	def checkout_merged(self) -> AbstractStep[CheckoutAndMergeResult]:
		return [i for i in self.env.pipeline if isinstance(i, CheckoutMerged) or (isinstance(i, CachingStep) and isinstance(i.step, CheckoutMerged))][0]
	
	@property
	def git_clone(self) -> AbstractStep[str]:
		return [i for i in self.env.pipeline if isinstance(i, GitClone) or (isinstance(i, CachingStep) and isinstance(i.step, GitClone))][0]

	@property
	def git_unmerge(self) -> AbstractStep[List[Tuple[str, str]]]:
		return [i for i in self.env.pipeline if isinstance(i, GitUnmerge) or (isinstance(i, CachingStep) and isinstance(i.step, GitUnmerge))][0]

	@property
	def mock_check(self) -> AbstractStep[Dict[str, HasVersion]]:
		return [i for i in self.env.pipeline if isinstance(i, MockDockerSwarmCheck) or (isinstance(i, CachingStep) and isinstance(i.step, MockDockerSwarmCheck))][0]

	def teardown(self) -> None:
		"""Clean up temporary directories"""
		if self.remote_dir:
			shutil.rmtree(self.remote_dir, ignore_errors=True)
		if self.local_dir:
			shutil.rmtree(self.local_dir, ignore_errors=True)

	def create_commit(self, repo: git.Repo, from_branch: str, to_branch: str, filename: str, content: str,
					  message: str) -> git.Commit:
		"""Create a commit in the repository

		If to_branch doesn't exist, it will be created from from_branch and checked out.
		"""
		if from_branch in [head.name for head in repo.heads]:
			repo.heads[from_branch].checkout()
		if from_branch != to_branch:
			if to_branch not in [head.name for head in repo.heads]:
				new_branch = repo.create_head(to_branch)
				new_branch.checkout()
			else:
				raise BaseException("Target branch already exists.")

		# Create commit
		file_path = os.path.join(repo.working_dir, filename)
		with open(file_path, 'w') as f:
			f.write(content)
		repo.index.add([filename])
		return repo.index.commit(message)

	def verify_working_directory_files(self, expected_files: List[Tuple[str, str]]) -> None:
		"""Verify that working directory contains exactly the expected files with correct content.

		Args:
			directory: Path to the working directory to verify
			expected_files: List of tuples (filename, expected_content)
		"""
		files_in_wd = set(os.listdir(self.local_dir)) - {'.git'}
		expected_filenames = {filename for filename, _ in expected_files}
		assert files_in_wd == expected_filenames, f"Expected files {expected_filenames}, got {files_in_wd}"

		for filename, expected_content in expected_files:
			with open(os.path.join(self.local_dir, filename)) as f:
				actual_content = f.read()
				assert actual_content == expected_content, f"{filename} has incorrect content. Expected '{expected_content}', got '{actual_content}'"

	def _safe_git_log(self, repo_path: str, title: str) -> str:
		def _as_text(value: object) -> str:
			if isinstance(value, bytes):
				return value.decode(errors='replace')
			return str(value)

		repo = git.Repo(repo_path)
		commits = list(repo.iter_commits("--all", max_count=30))
		refs = [
			f"{_as_text(it.commit)[:10]}:{_as_text(it.name)}, is_remote:{it.is_remote()}"
			for it in repo.refs
		]
		lines = [
			f"{_as_text(commit.hexsha)[:10]} (p{[_as_text(it.hexsha)[:10] for it in commit.parents]}): {_as_text(commit.message).splitlines()[0]}"
			for commit in commits
		]
		return f"[{title}] git log ({repo_path})\n{"\n".join(lines)}\nrefs:\n{"\n".join(refs)}"

	def print_git_logs(self) -> None:
		"""Print remote and local repository logs for debugging failed tests."""
		print(f"Version: {git.__version__}")
		
		print(self._safe_git_log(self.remote_dir, "remote"))
		print(self._safe_git_log(self.local_dir, "local"))

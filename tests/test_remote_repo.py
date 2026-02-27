"""
Helper classes and utilities for git integration tests.

This module provides reusable test fixtures and mock objects for testing
git operations in an isolated environment.
"""
from curses import version
import tempfile
import shutil
import os
from typing import Dict, Protocol, Tuple, Optional, TYPE_CHECKING, List, Callable
import git  # type: ignore

from steps.docker import DockerSwarmCheck, DockerSwarmCheckResult  # noqa: F811
from steps.git import CheckoutMerged, GitUnmerge, GitClone  # noqa: F401
from enironment import Environment


class MockDockerSwarmCheck(DockerSwarmCheck):
    """Mock DockerSwarmCheck object for testing"""

    def __init__(self, version: Callable[[], str]) -> None:
        self.version = version
        self.stack_name = "test_stack"

    def progress(self) -> Dict[str, DockerSwarmCheckResult]:
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
    checkout_merged: CheckoutMerged
    git_clone: GitClone
    git_unmerge :GitUnmerge
    mock_check: MockDockerSwarmCheck

    def __init__(self) -> None:
        self.remote_dir = tempfile.mkdtemp(prefix="test_remote_")
        self.local_dir = tempfile.mkdtemp(prefix="test_local_")
        self.repo = git.Repo.init(self.remote_dir, bare=False)
        # Configure git user
        with self.repo.config_writer() as cw:
            cw.set_value("user", "email", "test@example.com")
            cw.set_value("user", "name", "Test User")
        self.env = Environment(
            id="test1",
            branches=[],
            dry=False,
            repo=self.remote_dir
        )
        
        # mock_wd = MockGitClone(repo_helper.local_dir, env)
        self.git_clone = GitClone(self.env, path=self.local_dir)
        self.mock_check = MockDockerSwarmCheck(lambda: f"auto-{self.checkout_merged.progress().version}")
        print(f"Cloning repo from {self.remote_dir} to {self.local_dir}")
        # Test CheckoutMerged
        self.checkout_merged = CheckoutMerged(
            wd=self.git_clone,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=self.env
        )
        self.git_unmerge = GitUnmerge(
            wd=self.git_clone,
            check=self.mock_check,
            env=self.env
        )


    def teardown(self) -> None:
        """Clean up temporary directories"""
        if self.remote_dir:
            shutil.rmtree(self.remote_dir, ignore_errors=True)
        if self.local_dir:
            shutil.rmtree(self.local_dir, ignore_errors=True)

    def create_commit(self, repo: git.Repo, from_branch: str, to_branch: str, filename: str, content: str, message: str) -> git.Commit:  # type: ignore
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

    def clone_repo(self) -> git.Repo:  # type: ignore
        """Clone the remote repository to local directory"""
        clone_repo = git.Repo.clone_from(self.remote_dir, self.local_dir)
        clone_repo.remotes.origin.fetch()
        return clone_repo

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


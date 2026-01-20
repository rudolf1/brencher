"""
Helper classes and utilities for git integration tests.

This module provides reusable test fixtures and mock objects for testing
git operations in an isolated environment.
"""
import tempfile
import shutil
import os
from typing import Tuple, Optional, TYPE_CHECKING
import git  # type: ignore

from steps.docker import DockerSwarmCheckResult  # noqa: F811
from steps.git import CheckoutMerged, GitUnmerge, GitClone  # noqa: F401
from enironment import Environment


class MockDockerSwarmCheck:
    """Mock DockerSwarmCheck object for testing"""

    def __init__(self, version: str) -> None:
        self.result = {
            "service1": DockerSwarmCheckResult(
                name="service1",
                version=version,
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


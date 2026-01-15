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

if TYPE_CHECKING:
    from steps.docker import DockerSwarmCheckResult  # noqa: F401
    from enironment import Environment


class RemoteRepoHelper:
    """Helper class for creating and managing test git repositories"""

    def __init__(self) -> None:
        self.remote_dir: Optional[str] = None
        self.local_dir: Optional[str] = None

    def setup(self) -> Tuple[str, str]:
        """Create temporary directories for remote and local repos"""
        self.remote_dir = tempfile.mkdtemp(prefix="test_remote_")
        self.local_dir = tempfile.mkdtemp(prefix="test_local_")
        return self.remote_dir, self.local_dir

    def teardown(self) -> None:
        """Clean up temporary directories"""
        if self.remote_dir:
            shutil.rmtree(self.remote_dir, ignore_errors=True)
        if self.local_dir:
            shutil.rmtree(self.local_dir, ignore_errors=True)

    def setup_remote_repo(self, repo_path: str) -> git.Repo:  # type: ignore
        """Initialize a remote repository (non-bare for testing purposes)"""
        repo = git.Repo.init(repo_path, bare=False)
        # Configure git user
        with repo.config_writer() as cw:
            cw.set_value("user", "email", "test@example.com")
            cw.set_value("user", "name", "Test User")
        return repo

    def create_commit(self, repo: git.Repo, filename: str, content: str, message: str) -> git.Commit:  # type: ignore
        """Create a commit in the repository"""
        file_path = os.path.join(repo.working_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        repo.index.add([filename])
        return repo.index.commit(message)

    def clone_repo(self, remote_dir: str, local_dir: str) -> git.Repo:  # type: ignore
        """Clone the remote repository to local directory"""
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)
        clone_repo.remotes.origin.fetch()
        return clone_repo


class MockGitClone:
    """Mock GitClone object for testing"""

    def __init__(self, result_path: str, env: 'Environment') -> None:
        self.result = result_path
        self.result_obj = result_path
        self.env = env


class MockDockerSwarmCheck:
    """Mock DockerSwarmCheck object for testing"""

    def __init__(self, version: str) -> None:
        from steps.docker import DockerSwarmCheckResult  # noqa: F811
        self.result = {
            "service1": DockerSwarmCheckResult(
                name="service1",
                version=version,
                image="test:latest",
                stack="test-stack"
            )
        }

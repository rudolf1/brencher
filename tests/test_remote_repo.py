"""
Helper classes and utilities for git integration tests.

This module provides reusable test fixtures and mock objects for testing
git operations in an isolated environment.
"""
import tempfile
import shutil
import os
import sys
from pathlib import Path
import git
from typing import Tuple

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from enironment import Environment
from steps.docker import DockerSwarmCheckResult


class RemoteRepoHelper:
    """Helper class for creating and managing test git repositories"""
    
    def __init__(self):
        self.remote_dir = None
        self.local_dir = None
    
    def setup(self) -> Tuple[str, str]:
        """Create temporary directories for remote and local repos"""
        self.remote_dir = tempfile.mkdtemp(prefix="test_remote_")
        self.local_dir = tempfile.mkdtemp(prefix="test_local_")
        return self.remote_dir, self.local_dir
    
    def teardown(self):
        """Clean up temporary directories"""
        if self.remote_dir:
            shutil.rmtree(self.remote_dir, ignore_errors=True)
        if self.local_dir:
            shutil.rmtree(self.local_dir, ignore_errors=True)
    
    def setup_remote_repo(self, repo_path: str) -> git.Repo:
        """Initialize a remote repository (non-bare for testing purposes)"""
        repo = git.Repo.init(repo_path, bare=False)
        # Configure git user
        with repo.config_writer() as cw:
            cw.set_value("user", "email", "test@example.com")
            cw.set_value("user", "name", "Test User")
        return repo
    
    def create_commit(self, repo: git.Repo, filename: str, content: str, message: str) -> git.Commit:
        """Create a commit in the repository"""
        file_path = os.path.join(repo.working_dir, filename)
        with open(file_path, 'w') as f:
            f.write(content)
        repo.index.add([filename])
        return repo.index.commit(message)
    
    def clone_repo(self, remote_dir: str, local_dir: str) -> git.Repo:
        """Clone the remote repository to local directory"""
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)
        clone_repo.remotes.origin.fetch()
        return clone_repo


class MockGitClone:
    """Mock GitClone object for testing"""
    
    def __init__(self, result_path: str, env: Environment):
        self.result = result_path
        self.result_obj = result_path
        self.env = env


class MockDockerSwarmCheck:
    """Mock DockerSwarmCheck object for testing"""
    
    def __init__(self, version: str):
        self.result = {
            "service1": DockerSwarmCheckResult(
                name="service1",
                version=version,
                image="test:latest",
                stack="test-stack"
            )
        }

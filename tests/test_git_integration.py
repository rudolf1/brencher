"""
Integration tests for git.py classes: CheckoutMerged and GitUnmerge

These tests run in a Docker-like isolated environment to avoid harming the host system.
They simulate remote and local git repositories and test various merge scenarios.
"""
import tempfile
import shutil
import os
import sys
from pathlib import Path
import pytest
import git

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from steps.git import CheckoutMerged, GitUnmerge, CheckoutAndMergeResult
from enironment import Environment
from steps.docker import DockerSwarmCheckResult


class TestGitIntegration:
    """Integration tests for git operations"""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for remote and local repos"""
        remote_dir = tempfile.mkdtemp(prefix="test_remote_")
        local_dir = tempfile.mkdtemp(prefix="test_local_")
        yield remote_dir, local_dir
        # Cleanup
        shutil.rmtree(remote_dir, ignore_errors=True)
        shutil.rmtree(local_dir, ignore_errors=True)

    def setup_remote_repo(self, repo_path: str) -> git.Repo:
        """Initialize a bare remote repository"""
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

    def test_checkout_merged_two_branches(self, temp_dirs):
        """Test merging two branches successfully"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1 from main
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Switch to main and create branch2
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = self.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Create a GitClone-like working directory
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment
        env = Environment(
            id="test1",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        # Create a mock GitClone object
        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Test CheckoutMerged
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result = checkout_merged.progress()

        # Verify result
        assert isinstance(result, CheckoutAndMergeResult)
        assert result.branch_name.startswith("auto/")
        assert result.commit_hash is not None
        assert result.version is not None

    def test_checkout_merged_three_branches(self, temp_dirs):
        """Test merging three branches successfully"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Create branch2 from main
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = self.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Create branch3 from main
        remote_repo.heads.master.checkout()
        branch3 = remote_repo.create_head("branch3")
        branch3.checkout()
        commit4 = self.create_commit(remote_repo, "file4.txt", "content4", "Branch3 commit")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment with 3 branches
        env = Environment(
            id="test2",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD"), ("branch3", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Test CheckoutMerged
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result = checkout_merged.progress()

        # Verify result
        assert isinstance(result, CheckoutAndMergeResult)
        assert result.branch_name.startswith("auto/")
        assert result.commit_hash is not None

    def test_checkout_merged_fast_forward(self, temp_dirs):
        """Test merging with fast-forward (linear history)"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1 from main
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit 1")  # noqa: F841
        commit3 = self.create_commit(remote_repo, "file3.txt", "content3", "Branch1 commit 2")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment - trying to merge main and branch1 (fast-forward possible)
        env = Environment(
            id="test3",
            branches=[("master", "HEAD"), ("branch1", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Test CheckoutMerged
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result = checkout_merged.progress()

        # Verify result - should find existing branch or create merge
        assert isinstance(result, CheckoutAndMergeResult)
        assert result.commit_hash is not None

    def test_checkout_merged_conflicting_branches(self, temp_dirs):
        """Test merging conflicting branches - should fail gracefully"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = self.create_commit(remote_repo, "file1.txt", "initial content", "Initial commit")  # noqa: F841

        # Create branch1 and modify file1.txt
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file1.txt", "branch1 content", "Branch1 change")  # noqa: F841

        # Create branch2 from main and modify the same file differently
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = self.create_commit(remote_repo, "file1.txt", "branch2 content", "Branch2 change")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment
        env = Environment(
            id="test4",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Test CheckoutMerged - should raise exception on conflict
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        # Expect merge conflict to be raised as BaseException
        with pytest.raises(BaseException, match="Merge conflict"):
            checkout_merged.progress()

    def test_checkout_merged_existing_auto_branch(self, temp_dirs):
        """Test that existing auto branch is reused"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Create branch2 from main
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = self.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment
        env = Environment(
            id="test5",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # First merge - creates auto branch
        checkout_merged1 = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result1 = checkout_merged1.progress()
        auto_branch_name = result1.branch_name

        # Second merge with same branches - should reuse existing auto branch
        checkout_merged2 = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result2 = checkout_merged2.progress()

        # Verify same auto branch is used
        assert result2.branch_name == auto_branch_name
        assert result2.commit_hash == result1.commit_hash

    def test_git_unmerge_valid_version(self, temp_dirs):
        """Test GitUnmerge with valid auto version string"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)

        # Create commits
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = self.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = self.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841
        clone_repo.remotes.origin.fetch()

        # Create environment
        env = Environment(
            id="test6",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        # Mock GitClone
        class MockGitClone:
            def __init__(self, result_path):
                self.result = result_path
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Mock DockerSwarmCheck with version string
        version_str = f"auto-{commit2.hexsha[:8]}-{commit3.hexsha[:8]}"

        class MockDockerSwarmCheck:
            def __init__(self):
                self.result = {
                    "service1": DockerSwarmCheckResult(
                        name="service1",
                        version=version_str,
                        image="test:latest",
                        stack="test-stack"
                    )
                }

        mock_check = MockDockerSwarmCheck()

        # Test GitUnmerge
        git_unmerge = GitUnmerge(
            wd=mock_wd,
            check=mock_check,
            env=env
        )

        result = git_unmerge.progress()

        # Verify result contains branch information
        assert isinstance(result, list)
        assert len(result) > 0
        for branch_name, commit_hash in result:
            assert isinstance(branch_name, str)
            assert isinstance(commit_hash, str)

    def test_git_unmerge_invalid_version(self, temp_dirs):
        """Test GitUnmerge with invalid version format"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841

        # Create environment
        env = Environment(
            id="test7",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result = result_path
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Mock DockerSwarmCheck with invalid version format
        class MockDockerSwarmCheck:
            def __init__(self):
                self.result = {
                    "service1": DockerSwarmCheckResult(
                        name="service1",
                        version="invalid-version-format",
                        image="test:latest",
                        stack="test-stack"
                    )
                }

        mock_check = MockDockerSwarmCheck()

        # Test GitUnmerge - should raise exception
        git_unmerge = GitUnmerge(
            wd=mock_wd,
            check=mock_check,
            env=env
        )

        with pytest.raises(BaseException, match="Version format not recognized"):
            git_unmerge.progress()

    def test_checkout_merged_empty_branches(self, temp_dirs):
        """Test CheckoutMerged with empty branches list - should fail"""
        remote_dir, local_dir = temp_dirs

        # Setup remote repository
        remote_repo = self.setup_remote_repo(remote_dir)
        commit1 = self.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Clone repository
        clone_repo = git.Repo.clone_from(remote_dir, local_dir)  # noqa: F841

        # Create environment with empty branches
        env = Environment(
            id="test8",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        class MockGitClone:
            def __init__(self, result_path):
                self.result_obj = result_path
                self.env = env

        mock_wd = MockGitClone(local_dir)

        # Test CheckoutMerged - should raise exception
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        with pytest.raises(BaseException, match="Empty branches set"):
            checkout_merged.progress()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

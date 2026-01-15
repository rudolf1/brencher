"""
Integration tests for git.py classes: CheckoutMerged and GitUnmerge

These tests run in a Docker-like isolated environment to avoid harming the host system.
They simulate remote and local git repositories and test various merge scenarios.
"""
import pytest  # type: ignore
from typing import Generator


from steps.git import CheckoutMerged, GitUnmerge, CheckoutAndMergeResult
from enironment import Environment
from tests.test_remote_repo import RemoteRepoHelper, MockGitClone, MockDockerSwarmCheck


class TestGitIntegration:
    """Integration tests for git operations"""

    @pytest.fixture
    def repo_helper(self) -> Generator[RemoteRepoHelper, None, None]:
        """Create a repository helper instance"""
        helper = RemoteRepoHelper()
        remote_dir, local_dir = helper.setup()
        yield helper
        helper.teardown()

    def test_checkout_merged_two_branches(self, repo_helper: RemoteRepoHelper) -> None:
        """Test merging two branches successfully"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1 from main
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Switch to main and create branch2
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Create a GitClone-like working directory
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test1",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        # Create mock GitClone object
        mock_wd = MockGitClone(local_dir, env)

        # Test CheckoutMerged
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result = checkout_merged.progress()

        # Verify result with specific field checks
        assert isinstance(result, CheckoutAndMergeResult)
        assert result.branch_name.startswith("auto/"), f"Expected auto branch, got {result.branch_name}"
        assert len(result.commit_hash) == 40, f"Invalid commit hash length: {result.commit_hash}"
        assert result.commit_hash.isalnum(), f"Commit hash should be alphanumeric: {result.commit_hash}"
        assert "-" in result.version, f"Version should contain '-': {result.version}"
        assert len(result.version.split("-")) == 2, f"Version should have 2 parts: {result.version}"

    def test_checkout_merged_three_branches(self, repo_helper: RemoteRepoHelper) -> None:
        """Test merging three branches successfully"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Create branch2 from main
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Create branch3 from main
        remote_repo.heads.master.checkout()
        branch3 = remote_repo.create_head("branch3")
        branch3.checkout()
        commit4 = repo_helper.create_commit(remote_repo, "file4.txt", "content4", "Branch3 commit")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment with 3 branches
        env = Environment(
            id="test2",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD"), ("branch3", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)

        # Test CheckoutMerged
        checkout_merged = CheckoutMerged(
            wd=mock_wd,
            git_user_email="test@example.com",
            git_user_name="Test User",
            push=False,
            env=env
        )

        result = checkout_merged.progress()

        # Verify result with specific field checks
        assert isinstance(result, CheckoutAndMergeResult)
        assert result.branch_name.startswith("auto/"), f"Expected auto branch, got {result.branch_name}"
        assert len(result.commit_hash) == 40, f"Invalid commit hash length: {result.commit_hash}"
        assert result.commit_hash.isalnum(), f"Commit hash should be alphanumeric: {result.commit_hash}"
        assert len(result.version.split("-")) == 3, f"Version should have 3 parts for 3 branches: {result.version}"

    def test_checkout_merged_fast_forward(self, repo_helper: RemoteRepoHelper) -> None:
        """Test merging with fast-forward (linear history)"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1 from main
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit 1")  # noqa: F841
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch1 commit 2")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment - trying to merge main and branch1 (fast-forward possible)
        env = Environment(
            id="test3",
            branches=[("master", "HEAD"), ("branch1", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)

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
        assert len(result.commit_hash) == 40, f"Invalid commit hash length: {result.commit_hash}"
        assert result.commit_hash.isalnum(), f"Commit hash should be alphanumeric: {result.commit_hash}"

    def test_checkout_merged_conflicting_branches(self, repo_helper: RemoteRepoHelper) -> None:
        """Test merging conflicting branches - should fail gracefully"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "initial content", "Initial commit")  # noqa: F841

        # Create branch1 and modify file1.txt
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file1.txt", "branch1 content", "Branch1 change")  # noqa: F841

        # Create branch2 from main and modify the same file differently
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = repo_helper.create_commit(remote_repo, "file1.txt", "branch2 content", "Branch2 change")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test4",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)

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

    def test_checkout_merged_existing_auto_branch(self, repo_helper: RemoteRepoHelper) -> None:
        """Test that existing auto branch is reused"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create main branch with initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")  # noqa: F841

        # Create branch2 from main
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test5",
            branches=[("branch1", "HEAD"), ("branch2", "HEAD")],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)

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

        # Verify same auto branch is used with actual value checks
        assert result2.branch_name == auto_branch_name, f"Expected {auto_branch_name}, got {result2.branch_name}"
        assert result2.commit_hash == result1.commit_hash, f"Expected {result1.commit_hash}, got {result2.commit_hash}"
        assert len(result2.commit_hash) == 40, f"Invalid commit hash length: {result2.commit_hash}"

    def test_checkout_merged_and_unmerge_valid_version(self, repo_helper: RemoteRepoHelper) -> None:
        """Test merging branches and then unmerging with valid version string"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create commits
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit")

        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch2 commit")

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test6",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        # Mock GitClone
        mock_wd = MockGitClone(local_dir, env)

        # Mock DockerSwarmCheck with version string
        version_str = f"auto-{commit2.hexsha[:8]}-{commit3.hexsha[:8]}"
        mock_check = MockDockerSwarmCheck(version_str)

        # Test GitUnmerge
        git_unmerge = GitUnmerge(
            wd=mock_wd,
            check=mock_check,
            env=env
        )

        result = git_unmerge.progress()

        # Verify result contains branch information with specific value checks
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Result should not be empty"

        for branch_name, commit_hash in result:
            assert isinstance(branch_name, str), f"Branch name should be string, got {type(branch_name)}"
            assert len(branch_name) > 0, "Branch name should not be empty"
            assert isinstance(commit_hash, str), f"Commit hash should be string, got {type(commit_hash)}"
            assert len(commit_hash) == 40, f"Commit hash should be 40 chars, got {len(commit_hash)}: {commit_hash}"
            assert commit_hash.isalnum(), f"Commit hash should be alphanumeric: {commit_hash}"

    def test_git_unmerge_invalid_version(self, repo_helper: RemoteRepoHelper) -> None:
        """Test GitUnmerge with invalid version format"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test7",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)
        mock_check = MockDockerSwarmCheck("invalid-version-format")

        # Test GitUnmerge - should raise exception
        git_unmerge = GitUnmerge(
            wd=mock_wd,
            check=mock_check,
            env=env
        )

        with pytest.raises(BaseException, match="Version format not recognized"):
            git_unmerge.progress()

    @pytest.mark.xfail(
        reason="GitUnmerge does not yet support finding branches for non-HEAD commits. "
               "Implementation needs to search through branch history.")
    def test_git_unmerge_nonhead_commit(self, repo_helper: RemoteRepoHelper) -> None:
        """Test GitUnmerge when version corresponds to non-HEAD commit in a branch

        This test verifies the EXPECTED behavior (not current implementation) when a
        commit in the version string is not the HEAD of any branch but exists in a
        branch's history.

        EXPECTED: GitUnmerge should return branch1 with commit2, even though commit2
        is not the HEAD of branch1.

        NOTE: This test WILL FAIL until GitUnmerge is updated to search through branch
        history to find branches containing non-HEAD commits.
        """
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)

        # Create initial commit
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Create branch1 with multiple commits
        branch1 = remote_repo.create_head("branch1")
        branch1.checkout()
        commit2 = repo_helper.create_commit(remote_repo, "file2.txt", "content2", "Branch1 commit 1")
        commit3 = repo_helper.create_commit(remote_repo, "file3.txt", "content3", "Branch1 commit 2")  # noqa: F841

        # Create branch2 from master
        remote_repo.heads.master.checkout()
        branch2 = remote_repo.create_head("branch2")
        branch2.checkout()
        commit4 = repo_helper.create_commit(remote_repo, "file4.txt", "content4", "Branch2 commit")

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment
        env = Environment(
            id="test_nonhead",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        # Mock GitClone
        mock_wd = MockGitClone(local_dir, env)

        # Mock DockerSwarmCheck with version string using non-HEAD commit from branch1
        # commit2 is NOT the HEAD of branch1 (commit3 is), but it exists in branch1's history
        version_str = f"auto-{commit2.hexsha[:8]}-{commit4.hexsha[:8]}"
        mock_check = MockDockerSwarmCheck(version_str)

        # Test GitUnmerge
        git_unmerge = GitUnmerge(
            wd=mock_wd,
            check=mock_check,
            env=env
        )

        result = git_unmerge.progress()

        # Verify result contains branch information
        assert isinstance(result, list)
        assert len(result) >= 1  # At least branch2 should be found

        # Extract branch names and commit hashes
        result_dict = {commit_hash: branch_name for branch_name, commit_hash in result}

        # commit4 should be in the results (HEAD of branch2)
        assert commit4.hexsha in result_dict, f"Expected commit4 {commit4.hexsha} (HEAD of branch2) in results"
        assert result_dict[commit4.hexsha] == "branch2", "branch2 should be associated with commit4"

        # For commit2 (non-HEAD commit in branch1), it SHOULD be returned with branch1
        # Even though commit2 is not the HEAD of branch1, GitUnmerge should search
        # through branch history to find branches containing the commit.
        # This test will fail until GitUnmerge is updated to support non-HEAD commits.

        assert commit2.hexsha in result_dict, \
            f"Expected commit2 {commit2.hexsha} (non-HEAD commit in branch1) to be in results. " \
            f"GitUnmerge should return branch1 even when commit2 is not HEAD. " \
            f"Current results: {result}"

        assert result_dict[commit2.hexsha] == "branch1", \
            f"branch1 should be associated with commit2. Got: {result_dict.get(commit2.hexsha)}"

    def test_checkout_merged_empty_branches(self, repo_helper: RemoteRepoHelper) -> None:
        """Test CheckoutMerged with empty branches list - should fail"""
        remote_dir = repo_helper.remote_dir
        local_dir = repo_helper.local_dir

        # Setup remote repository
        remote_repo = repo_helper.setup_remote_repo(remote_dir)
        commit1 = repo_helper.create_commit(remote_repo, "file1.txt", "content1", "Initial commit")  # noqa: F841

        # Clone repository
        repo_helper.clone_repo(remote_dir, local_dir)

        # Create environment with empty branches
        env = Environment(
            id="test8",
            branches=[],
            dry=False,
            repo=remote_dir
        )

        mock_wd = MockGitClone(local_dir, env)

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

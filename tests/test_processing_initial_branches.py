import json

import pytest

from enironment import SharedStateConflictError
from processing import process_all_jobs
from steps.git import GitClone
from steps.shared_state import SharedStateHolderInGit
from tests.test_remote_repo import RemoteRepoHelper


class TestInitialBranches:
    """Integration tests for git operations"""

    def test_process_all_jobs_resolves_initial_branches_and_persists_state(self, repo_helper: RemoteRepoHelper) -> None:
        _ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
        commit2 = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2",
                                            "Branch1 commit")
        commit3 = repo_helper.create_commit(repo_helper.repo, "master", "branch2", "file3.txt", "content3",
                                            "Branch2 commit")

        repo_helper.set_desired_branches([("branch1", "HEAD"), ("branch2", "HEAD")])

        has_error = process_all_jobs([repo_helper.env], lambda: None)
        assert has_error is False
        assert repo_helper.get_desired_branches() == [("branch1", "HEAD"), ("branch2", "HEAD")]

        state_raw = repo_helper.repo.git.show("brencher-state:.brencher/branches-state.json")
        state = json.loads(state_raw)
        assert state[repo_helper.env.id]["branches"] == [["branch1", "HEAD"], ["branch2", "HEAD"]]
        assert state[repo_helper.env.id]["repo"] == repo_helper.env.repo

        result = repo_helper.checkout_merged.progress()
        assert commit2.hexsha[:8] in result.version
        assert commit3.hexsha[:8] in result.version


    def test_resolve_initial_branches_rejects_stale_token(self, repo_helper: RemoteRepoHelper) -> None:
        _ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
        _ = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2", "Branch1 commit")
        _ = repo_helper.create_commit(repo_helper.repo, "state", "state", "blank.txt", "", "Branch1 commit")

        clone = GitClone(repo_helper.env.repo)
        clone.env = repo_helper.env
        resolve_step = SharedStateHolderInGit(clone, state_branch="state")
        resolve_step.env = repo_helper.env
        stale_token = resolve_step.progress().token
        assert isinstance(stale_token, str)

        resolve_step.set_branches([("branch1", "HEAD")], expected_token=stale_token)

        with pytest.raises(SharedStateConflictError, match="State token mismatch"):
            resolve_step.set_branches([("master", "HEAD")], expected_token=stale_token)

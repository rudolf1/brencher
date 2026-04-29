import json

import pytest

from enironment import SharedStateConflictError
from processing import process_all_jobs
from steps.git import GitClone
from steps.shared_state import SharedStateHolderInGit
from tests.test_remote_repo import RemoteRepoHelper


class TestInitialBranches:
    """Integration tests for git operations"""

    def test_resolve_initial_branches(self, repo_helper: RemoteRepoHelper) -> None:
        _ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
        _ = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2", "Branch1 commit")
        _ = repo_helper.create_commit(repo_helper.repo, "state", "state", "blank.txt", "", "Branch1 commit")

        clone = GitClone(url=repo_helper.local_dir)
        clone.env = repo_helper.env
        cloneState = GitClone(url=repo_helper.local_dir, n='state')
        cloneState.env = repo_helper.env
        resolve_step = SharedStateHolderInGit(clone, state_repo=cloneState, state_branch="state")
        resolve_step.env = repo_helper.env
        stale_token = resolve_step.progress().token
        assert isinstance(stale_token, str)

        t = resolve_step.set_branches([("branch1", "HEAD")], expected_token=stale_token).token
        t = resolve_step.set_dry(True, expected_token=t).token

        with pytest.raises(SharedStateConflictError, match="State token mismatch"):
            resolve_step.set_branches([("master", "HEAD")], expected_token=stale_token)

        t = resolve_step.set_branches([("master", "HEAD")], expected_token=t).token

        t = resolve_step.set_dry(False, expected_token=t).token

        jpl = repo_helper.repo.git.show(f"state:{repo_helper.env.id}.json")
        pl = json.loads(jpl)
        assert pl['branches'] == [["master", "HEAD"]]
        assert pl['dry'] == False
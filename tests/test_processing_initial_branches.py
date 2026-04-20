import json
import os
import tempfile

import git
import pytest

from processing import process_all_jobs
from steps.git import ResolveInitialBranches
from tests.test_remote_repo import RemoteRepoHelper


def test_process_all_jobs_resolves_initial_branches_and_persists_state(repo_helper: RemoteRepoHelper) -> None:
	_ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
	commit2 = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2", "Branch1 commit")
	commit3 = repo_helper.create_commit(repo_helper.repo, "master", "branch2", "file3.txt", "content3", "Branch2 commit")

	repo_helper.env.branches = []
	repo_helper.mock_check.version = lambda: f"auto-{commit2.hexsha[:8]}-{commit3.hexsha[:8]}"  # type: ignore[attr-defined]

	has_error = process_all_jobs([repo_helper.env], lambda: None)
	assert has_error is False
	assert repo_helper.env.branches == [("branch1", commit2.hexsha), ("branch2", commit3.hexsha)]

	state_raw = repo_helper.repo.git.show("brencher-state:.brencher/branches-state.json")
	state = json.loads(state_raw)
	assert state[repo_helper.env.id]["branches"] == [["branch1", commit2.hexsha], ["branch2", commit3.hexsha]]
	assert state[repo_helper.env.id]["repo"] == repo_helper.env.repo


def test_resolve_initial_branches_reports_push_conflict(repo_helper: RemoteRepoHelper, monkeypatch: pytest.MonkeyPatch) -> None:
	_ = repo_helper.create_commit(repo_helper.repo, "master", "master", "file1.txt", "content1", "Initial commit")
	commit2 = repo_helper.create_commit(repo_helper.repo, "master", "branch1", "file2.txt", "content2", "Branch1 commit")

	repo_helper.env.branches = []
	repo_helper.mock_check.version = lambda: f"auto-{commit2.hexsha[:8]}"  # type: ignore[attr-defined]

	resolve_step = ResolveInitialBranches(
		wd=repo_helper.git_clone,
		unmerge=repo_helper.git_unmerge,
	)
	resolve_step.env = repo_helper.env
	resolve_step.progress()
	repo_helper.env.branches = []

	orig_checkout = resolve_step._checkout_state_branch

	def checkout_and_modify_remote(repo: git.Repo) -> None:
		orig_checkout(repo)
		with tempfile.TemporaryDirectory(prefix="test_remote_writer_") as tmp_dir:
			other_clone = git.Repo.clone_from(repo_helper.remote_dir, tmp_dir)
			other_clone.git.checkout("-B", "brencher-state", "origin/brencher-state")
			state_file = os.path.join(tmp_dir, ".brencher", "branches-state.json")
			with open(state_file) as f:
				state = json.load(f)
			state[repo_helper.env.id]["updated_by"] = "other-writer"
			with open(state_file, "w") as f:
				json.dump(state, f, sort_keys=True, indent=2)
				f.write("\n")
			other_clone.index.add([".brencher/branches-state.json"])
			other_clone.index.commit("Concurrent update")
			other_clone.git.push("origin", "HEAD:refs/heads/brencher-state")

	monkeypatch.setattr(resolve_step, "_checkout_state_branch", checkout_and_modify_remote)

	with pytest.raises(Exception, match="Conflict while pushing initial branches state"):
		resolve_step.progress()

	assert repo_helper.env.branches == []

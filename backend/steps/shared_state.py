import hashlib
import tempfile
from dataclasses import dataclass, replace
from typing import List, Tuple, Any, Protocol, runtime_checkable
import json
import os
import logging
import git
import threading


from enironment import AbstractStep, SharedState, SharedStateHolder
from steps.git import GitUnmergeResult

logger = logging.getLogger(__name__)

class SharedStateHolderInMemory(AbstractStep[SharedState], SharedStateHolder):

    def __init__(self, unmerge: AbstractStep[GitUnmergeResult] | None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = SharedState([], True)
        self.unmerge = unmerge

    def set_branches(self, branches: List[Tuple[str, str]]) -> None:
        self.state = replace(self.state, branches=branches)

    def set_dry(self, dry: bool) -> None:
        self.state = replace(self.state, dry=dry)

    def progress(self) -> SharedState:
        if len(self.state.branches) == 0:
            if self.unmerge:
                unmerge = self.unmerge.progress()
                self.state = replace(self.state, branches=unmerge.branches)
        return self.state


class SharedStateHolderInGit(AbstractStep[SharedState], SharedStateHolder):

    def __init__(
            self,
            state_branch: str = "state",
            state_repo_url: str | None = None,
            **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.state_branch = state_branch
        self.state_repo_url = state_repo_url
        self._lock = threading.RLock()


    def set_branches(self, branches: List[Tuple[str, str]]) -> None:
        with self._lock:
            repo = self._ensure_repo()
            oldState = self._read(repo)
            newState = replace(oldState, branches=branches)
            self._write(repo, newState)

    def set_dry(self, dry: bool) -> None:
        with self._lock:
            repo = self._ensure_repo()
            oldState = self._read(repo)
            newState = replace(oldState, dry=dry)
            self._write(repo, newState)

    def progress(self) -> SharedState:
        with self._lock:
            repo = self._ensure_repo()
            return self._read(repo)

    def file_path(self, repo: git.Repo) -> str:
        return f"{repo.working_dir}/{self.env.id}.json"

    def _ensure_repo(self) -> git.Repo:

        state_repo_path = os.path.join(tempfile.gettempdir(),
                                       f"{self.env.id}_{hashlib.sha1(self.env.repo.encode()).hexdigest()[:5]}_state")

        repo = git.Repo(state_repo_path)

        if self.state_repo_url and repo.remotes.origin.url.rstrip("/") != self.state_repo_url.rstrip("/"):
            repo.remotes.origin.set_url(self.state_repo_url)
            repo.remotes.origin.fetch(prune=True)

        # Checkout state branch in detached HEAD state
        remote_state_ref = f"origin/{self.state_branch}"
        remote_refs = {ref.name for ref in repo.refs}
        if remote_state_ref in remote_refs:
            repo.git.checkout("--detach", remote_state_ref)
        else:
            # Find default branch
            default_remote_branch = "origin/master"
            try:
                default_remote_branch = repo.git.symbolic_ref("refs/remotes/origin/HEAD").replace("refs/remotes/", "")
            except Exception:
                for ref in repo.refs:
                    if ref.name.startswith("origin/") and ref.name != "origin/HEAD":
                        default_remote_branch = ref.name
                        break
            repo.git.checkout("--detach", default_remote_branch)

        return repo

    def _read(self, repo: git.Repo) -> SharedState:
        """Read state from Git repository state file.
        :param repo1:
        """
        state_abs_path = self.file_path(repo)

        os.makedirs(os.path.dirname(state_abs_path), exist_ok=True)
        
        state_data: dict[str, Any] = {}
        if os.path.exists(state_abs_path):
            try:
                with open(state_abs_path) as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in state file {state_abs_path}: {str(e)}") from e

        env_state = state_data.get(self.env.id, {})
        branches = self._state_entry_to_branches(env_state.get("branches", []))
        dry = env_state.get("dry", True)
        
        return SharedState(branches=branches, dry=dry)

    def _write(self, repo: git.Repo, state: SharedState) -> None:
        """Write state to Git repository state file.
        :param state1:
        """
        state_abs_path = self.file_path(repo)
        os.makedirs(os.path.dirname(state_abs_path), exist_ok=True)
        state_data = {
            "branches": state.branches,
            "dry": state.dry,
        }

        new_state_content = json.dumps(state_data, sort_keys=True, indent=2) + "\n"
        with open(state_abs_path, "w") as f:
            f.write(new_state_content)
        repo.index.add([state_abs_path])
        repo.index.commit(f"Update state for {self.env.id}")

        repo.git.push("origin", f"HEAD:refs/heads/{self.state_branch}")

    def _state_entry_to_branches(self, value: Any) -> List[Tuple[str, str]]:
        """Convert state entry to branches list."""
        if not isinstance(value, list):
            return []
        result: List[Tuple[str, str]] = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                result.append((str(item[0]), str(item[1])))
        return result


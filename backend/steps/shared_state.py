import hashlib
import json
import logging
import os
import tempfile
import threading
import uuid
from dataclasses import replace
from typing import List, Tuple, Any

import git

from enironment import AbstractStep, SharedState, SharedStateHolder, SharedStateConflictError
from steps.git import GitUnmergeResult, GitClone

logger = logging.getLogger(__name__)


def _normalize_branches(branches: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return sorted(branches, key=lambda x: (x[0], x[1]))


class SharedStateHolderInMemory(AbstractStep[SharedState], SharedStateHolder):

    def __init__(self, unmerge: AbstractStep[GitUnmergeResult] | None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.state = SharedState([], False, token=uuid.uuid4().hex)
        self.unmerge = unmerge

    def set_branches(self, branches: List[Tuple[str, str]], expected_token: str | None = None) -> SharedState:
        if expected_token is not None and expected_token != self.state.token:
            raise SharedStateConflictError("State token mismatch")
        self.state = replace(self.state, branches=_normalize_branches(branches), token=uuid.uuid4().hex)
        return self.state

    def set_dry(self, dry: bool, expected_token: str | None = None) -> SharedState:
        if expected_token is not None and expected_token != self.state.token:
            raise SharedStateConflictError("State token mismatch")
        self.state = replace(self.state, dry=dry, token=uuid.uuid4().hex)
        return self.state

    def progress(self) -> SharedState:
        if len(self.state.branches) == 0:
            if self.unmerge:
                unmerge = self.unmerge.progress()
                self.state = replace(self.state, branches=unmerge.branches, token=uuid.uuid4().hex)
        return self.state


class SharedStateHolderInGit(AbstractStep[SharedState], SharedStateHolder):

    def __init__(
            self,
            wd: GitClone,
            state_repo: GitClone,
            state_branch: str = "state",
            **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.state_branch = state_branch
        self.wd = wd
        self.state_repo = state_repo
        self._lock = threading.RLock()

    def set_branches(self, branches: List[Tuple[str, str]], expected_token: str | None = None) -> SharedState:
        with self._lock:
            repo = self._ensure_repo(expected_token)
            oldState = self._read(repo)
            if expected_token is not None and expected_token != oldState.token:
                raise SharedStateConflictError("State token mismatch")

            newState = replace(oldState, branches=_normalize_branches(branches))
            self._write(repo, newState)
            return self._read(repo)

    def set_dry(self, dry: bool, expected_token: str | None = None) -> SharedState:
        with self._lock:
            repo = self._ensure_repo(expected_token)
            oldState = self._read(repo)
            newState = replace(oldState, dry=dry)
            self._write(repo, newState)
            return self._read(repo)

    def progress(self) -> SharedState:
        with self._lock:
            repo = self._ensure_repo(None)
            return self._read(repo)

    def file_path(self, repo: git.Repo) -> str:
        return f"{repo.working_dir}/{self.env.id}.json"

    def _ensure_repo(self, token: str | None = None) -> git.Repo:
        repo_path = self.state_repo.progress()
        repo = git.Repo(repo_path)
        if token is None:
            # Checkout state branch in detached HEAD state
            token = f"origin/{self.state_branch}"
            remote_refs = {ref.name for ref in repo.refs}
            if not token in remote_refs:
                raise BaseException("Branch not found")

        repo.git.checkout("--detach", token)
        return repo

    def _read(self, repo: git.Repo) -> SharedState:
        state_abs_path = self.file_path(repo)

        os.makedirs(os.path.dirname(state_abs_path), exist_ok=True)

        state_data: dict[str, Any] = {}
        if os.path.exists(state_abs_path):
            try:
                with open(state_abs_path) as f:
                    state_data = json.load(f)
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON in state file {state_abs_path}: {str(e)}") from e

        branches: List[Tuple[str, str]] = []
        if isinstance(state_data.get("branches", []), list):
            for item in state_data.get("branches", []):
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    branches.append((str(item[0]), str(item[1])))
        dry = bool(state_data.get("dry", True))
        return SharedState(branches=branches, dry=dry, token=repo.head.commit.hexsha)

    def _write(self, repo: git.Repo, state: SharedState) -> None:
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
        try:
            remote_state_ref = f"origin/{self.state_branch}"
            repo.git.merge(remote_state_ref, no_edit=True)
            repo.git.push("origin", f"HEAD:refs/heads/{self.state_branch}")
        except git.GitCommandError as e:
            repo.git.merge("--abort")
            raise SharedStateConflictError("State token mismatch")


import tempfile
import git
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Union, Tuple
from steps.step import AbstractStep
import tempfile
import os
from enironment import Environment

logger = logging.getLogger(__name__)

class GitClone(AbstractStep[str]):
    def __init__(self, env: Environment, **kwargs):
        super().__init__(env, **kwargs)
        self.temp_dir = os.path.join(tempfile.gettempdir(), f"{self.env.id}_{hashlib.sha1(self.env.repo.encode()).hexdigest()[:5]}")

    def progress(self) -> str:

        logger.info(f"Cloning repository {self.env.repo} to {self.temp_dir}")
        os.makedirs(self.temp_dir, exist_ok=True)
        if os.path.exists(os.path.join(self.temp_dir, ".git")):
            logger.info(f"Repository already cloned at {self.temp_dir}, fetching updates.")
            repo = git.Repo(self.temp_dir)
            repo.remotes.origin.fetch()
        else:
            git.Repo.clone_from(self.env.repo, self.temp_dir)
        
        return self.temp_dir
            
import hashlib

class CheckoutMerged(AbstractStep[Tuple[str, str]]):
    wd: GitClone
    branches: List[str]

    def __init__(self, wd: GitClone, branches: List[str], **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.branches = branches


    def progress(self) -> Tuple[str, str]:
        if self.wd.result_obj is BaseException:
            raise self.wd.result_obj

        repo_path = self.wd.result_obj
        if not isinstance(repo_path, str):
            raise BaseException(f"Unknown repo path {repo_path}")
        
        if len(self.branches) == 0:
            raise BaseException(f"Empty branches set")

        # Open the repository
        repo = git.Repo(repo_path)

        logger.info(f"Selected branches: {self.branches}")
        # Extract commit ids for the selected branches
        commit_ids = []
        for branch in self.branches:
            commit = repo.commit(branch)
            commit_ids.append(commit.hexsha)

        # Calculate hash by commits (sorted for determinism)
        sorted_commits = sorted(commit_ids)
        commit_hash = hashlib.sha1(''.join(sorted_commits).encode()).hexdigest()
        logger.info(f"Commit ids for branches: {dict(zip(self.branches, commit_ids))}")
        logger.info(f"Hash by commits: {commit_hash}")
        # Generate hash from branch names
        # sorted_branches = sorted(self.branches)
        # branch_hash = hashlib.sha1(''.join(sorted_branches).encode()).hexdigest()
        auto_branch_name = f"auto/{commit_hash}"
        
        logger.info(f"Looking for existing auto branch: {auto_branch_name}")
        
        # Check if the auto branch already exists
        for remote_ref in repo.remotes.origin.refs:
            if remote_ref.name == f"origin/{auto_branch_name}":
                # Auto branch exists, fetch it
                logger.info(f"Found existing auto branch: {auto_branch_name}")
                repo.git.checkout(auto_branch_name)
                commit_hash = repo.head.commit.hexsha
                
                return (auto_branch_name, commit_hash)

        # Auto branch doesn't exist, create it
        logger.info(f"Creating new auto branch: {auto_branch_name}")
        
        # Start with the first branch
        base_branch = self.branches[0]
        repo.git.checkout(base_branch)
        
        # Create temporary branch for merging
        temp_branch = f"temp-merge-{commit_hash}"
        # Remove temp_branch if it exists
        if temp_branch in repo.heads:
            repo.git.branch('-D', temp_branch)
        repo.git.checkout('-b', temp_branch)
        
        # Merge the rest of the branches
        for branch in self.branches[1:]:
            try:
                logger.info(f"Merging branch: {branch}")
                repo.git.merge(branch, '--no-ff')
            except git.GitCommandError as e:
                # Handle merge conflicts according to predefined rules
                # For now, we'll abort the merge and report failure
                repo.git.merge('--abort')
                error_message = f"Merge conflict when merging {branch}: {str(e)}"
                logger.error(error_message)
                
                raise BaseException(error_message)
        
        # Create and push the auto branch
        repo.git.branch('-f', auto_branch_name)
        repo.git.checkout(auto_branch_name)
        commit_hash = repo.head.commit.hexsha
        repo.git.push('-f', 'origin', auto_branch_name)
        
        return (auto_branch_name,commit_hash)

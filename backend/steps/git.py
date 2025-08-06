import tempfile
import git
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Union, Tuple
from steps.step import AbstractStep
import tempfile
from enironment import Environment

logger = logging.getLogger(__name__)

@dataclass
class GitClone(AbstractStep):
    env: Environment = field(metadata={"ignore_json":True})
    result: Union[str, BaseException] = BaseException("No result yet")

    def progress(self) -> None:
        try:
            # Create temporary directory for the clone

            temp_dir = tempfile.mkdtemp(prefix=f"{self.env.id}_")
            
            # Clone the repository
            logger.info(f"Cloning repository {self.env.repo} to {temp_dir}")
            git.Repo.clone_from(self.env.repo, temp_dir)
            
            self.result = temp_dir
            
        except Exception as e:
            self.result = e

import hashlib

@dataclass
class CheckoutMerged(AbstractStep):
    wd: GitClone
    branches: List[str]
    result: Union[Tuple[str, str], BaseException] = BaseException("No result yet")

    def progress(self) -> None:
        if self.wd.result is BaseException:
            self.result = self.wd.result
            return

        repo_path = self.wd.result
        if not isinstance(repo_path, str):
            self.result = repo_path  # propagate the error (likely an exception)
            return
        
        try:
            # Open the repository
            repo = git.Repo(repo_path)
            
            # Generate hash from branch names
            sorted_branches = sorted(self.branches)
            branch_hash = hashlib.sha1(''.join(sorted_branches).encode()).hexdigest()
            auto_branch_name = f"auto/{branch_hash}"
            
            logger.info(f"Looking for existing auto branch: {auto_branch_name}")
            
            # Check if the auto branch already exists
            for remote_ref in repo.remotes.origin.refs:
                if remote_ref.name == f"origin/{auto_branch_name}":
                    # Auto branch exists, fetch it
                    logger.info(f"Found existing auto branch: {auto_branch_name}")
                    repo.git.checkout(auto_branch_name)
                    commit_hash = repo.head.commit.hexsha
                    
                    self.result = (auto_branch_name, commit_hash)
                    return 

            # Auto branch doesn't exist, create it
            logger.info(f"Creating new auto branch: {auto_branch_name}")
            
            # Start with the first branch
            base_branch = self.branches[0]
            repo.git.checkout(base_branch)
            
            # Create temporary branch for merging
            temp_branch = f"temp-merge-{branch_hash}"
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
                    
                    self.result = BaseException(error_message)
                    return
            
            # Create and push the auto branch
            repo.git.branch('-f', auto_branch_name)
            repo.git.checkout(auto_branch_name)
            commit_hash = repo.head.commit.hexsha
            repo.git.push('-f', 'origin', auto_branch_name)
            
            self.result = (auto_branch_name,commit_hash)
            
        except Exception as e:
            error_message = f"Failed to create merged branch: {str(e)}"
            logger.error(error_message)
            self.result = BaseException(error_message)
            return

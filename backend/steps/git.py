import tempfile
import git
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional
from steps.step import AbstractStep

logger = logging.getLogger(__name__)

@dataclass
class GitCloneResult:
    repo_path: str
    success: bool
    error_message: Optional[str] = None

class GitClone(AbstractStep):
    def progress(self) -> None:
        """
        Clone the Git repository to a temporary folder.
        
        Args:
            git_url: URL of the Git repository to clone
            
        Returns:
            GitCloneResult: Object containing the path to the cloned repo and status
        """
        try:
            # Create temporary directory for the clone
            temp_dir = tempfile.mkdtemp(prefix="brencher_")
            
            # Clone the repository
            logger.info(f"Cloning repository {git_url} to {temp_dir}")
            git.Repo.clone_from(git_url, temp_dir)
            
            return GitCloneResult(
                repo_path=temp_dir,
                success=True
            )
            
        except Exception as e:
            error_message = f"Failed to clone repository: {str(e)}"
            logger.error(error_message)
            
            return GitCloneResult(
                repo_path="",
                success=False,
                error_message=error_message
            )



@dataclass
class CheckoutMergedResult:
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class CheckoutMerged(AbstractStep):
    def progress(self) -> None:
        """
        Find or create an auto branch that represents the merged state of selected branches.
        
        Args:
            clone_result: Result from GitClone step containing repo path
            branches: List of branches to merge
            
        Returns:
            CheckoutMergedResult: Object with merged branch details
        """
        if not clone_result.success:
            return CheckoutMergedResult(
                success=False,
                error_message="Cannot checkout merged branches: Git clone failed"
            )
        
        repo_path = clone_result.repo_path
        
        try:
            # Open the repository
            repo = git.Repo(repo_path)
            
            # Generate hash from branch names
            sorted_branches = sorted(branches)
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
                    
                    return CheckoutMergedResult(
                        branch_name=auto_branch_name,
                        commit_hash=commit_hash,
                        success=True
                    )
            
            # Auto branch doesn't exist, create it
            logger.info(f"Creating new auto branch: {auto_branch_name}")
            
            # Start with the first branch
            base_branch = branches[0]
            repo.git.checkout(base_branch)
            
            # Create temporary branch for merging
            temp_branch = f"temp-merge-{branch_hash}"
            repo.git.checkout('-b', temp_branch)
            
            # Merge the rest of the branches
            for branch in branches[1:]:
                try:
                    logger.info(f"Merging branch: {branch}")
                    repo.git.merge(branch, '--no-ff')
                except git.GitCommandError as e:
                    # Handle merge conflicts according to predefined rules
                    # For now, we'll abort the merge and report failure
                    repo.git.merge('--abort')
                    error_message = f"Merge conflict when merging {branch}: {str(e)}"
                    logger.error(error_message)
                    
                    return CheckoutMergedResult(
                        success=False,
                        error_message=error_message
                    )
            
            # Create and push the auto branch
            repo.git.branch('-f', auto_branch_name)
            repo.git.checkout(auto_branch_name)
            commit_hash = repo.head.commit.hexsha
            repo.git.push('-f', 'origin', auto_branch_name)
            
            return CheckoutMergedResult(
                branch_name=auto_branch_name,
                commit_hash=commit_hash,
                success=True
            )
            
        except Exception as e:
            error_message = f"Failed to create merged branch: {str(e)}"
            logger.error(error_message)
            
            return CheckoutMergedResult(
                success=False,
                error_message=error_message
            )

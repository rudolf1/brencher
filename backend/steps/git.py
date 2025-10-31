import tempfile
import git
from git.objects import Commit
from git.refs import Reference
import logging
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Union, Tuple, Set, Iterator, Dict, Any
from steps.step import AbstractStep
import tempfile
import os
from enironment import Environment

logger = logging.getLogger(__name__)

class GitClone(AbstractStep[str]):
    def __init__(self, env: Environment, branchNamePrefix="", credEnvPrefix="", **kwargs):
        super().__init__(env, **kwargs)
        self.temp_dir = os.path.join(tempfile.gettempdir(), f"{self.env.id}_{hashlib.sha1(self.env.repo.encode()).hexdigest()[:5]}")
        self.branchNamePrefix = branchNamePrefix
        self.credEnvPrefix = credEnvPrefix

    def _get_auth_git_url(self, url: str) -> str:
        username = os.getenv(f'{self.credEnvPrefix}_USERNAME')
        password = os.getenv(f'{self.credEnvPrefix}_PASSWORD')
        if username and password:
            # Extract protocol and the rest of the URL
            protocol, rest = url.split('://')
            return f"{protocol}://{username}:{password}@{rest}"
        
        return url

    def progress(self) -> str:

        logger.info(f"Cloning repository {self.env.repo} to {self.temp_dir}")
        os.makedirs(self.temp_dir, exist_ok=True)
        if os.path.exists(os.path.join(self.temp_dir, ".git")):
            logger.info(f"Repository already cloned at {self.temp_dir}, fetching updates.")
            repo = git.Repo(self.temp_dir)
            result = repo.remotes.origin.fetch(prune=True)
            if not result or any(fetch_info.flags & fetch_info.ERROR for fetch_info in result):
                raise BaseException(f"Failed to fetch updates for {self.env.repo}")
        else:
            repo = git.Repo.init(self.temp_dir)
            repo.remotes.append(repo.create_remote(
                'origin', 
                self._get_auth_git_url(self.env.repo)
            ))
            if self.branchNamePrefix != "":
                repo.config_writer().set_value('remote "origin"',"fetch", f"+refs/heads/{self.branchNamePrefix}/*:refs/remotes/origin/{self.branchNamePrefix}/*").release()
            repo.remotes.origin.fetch(prune=True)
            if not os.path.exists(os.path.join(self.temp_dir, ".git")):
                raise BaseException(f"Failed to clone repository {self.env.repo} to {self.temp_dir}")
        
        return self.temp_dir
    

    def get_branches(self) -> Dict[str, List[Any]]:
        repo = git.Repo(self.temp_dir)
        result = {}
        for ref in repo.refs:
            if ref.name.startswith('origin/') and not ref.name.startswith('origin/HEAD'):
                branch_name = ref.name [len('origin/'):]
                if not branch_name.startswith('auto/'): # Skip auto branches
                    result[branch_name] = []
                    cmt = [ref.commit]
                    for _ in range(10):
                        for commit in cmt:
                            result[branch_name].append({
                                'hexsha': commit.hexsha,
                                'author': commit.author.name,
                                'date': commit.committed_datetime.isoformat(),
                                'message': commit.message.strip()
                            })

                        cmt = [p for c in cmt for p in c.parents]
        return result

import hashlib

@dataclass
class CheckoutAndMergeResult:
    branch_name: str
    commit_hash: str
    version: str

class CheckoutMerged(AbstractStep[CheckoutAndMergeResult]):
    wd: GitClone

    def __init__(self, wd: GitClone,
                        git_user_email,
                        git_user_name,
                        push: bool = True,
                  **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.git_user_email = git_user_email
        self.git_user_name = git_user_name
        self.push = push

    def _commits_tree(self, repo: git.Repo) -> Dict[Commit, List[Commit]]:
        childs: Dict[Commit, List[Commit]] = {}
        for c in list(repo.iter_commits('--all')):
            for p in c.parents:
                childs.setdefault(p, []).append(c)
        return childs

    def _find_merge_childs(self, tree: Dict[Commit, List[Commit]], commit: Commit) -> List[Commit]:

        visited = [commit]
        queue = [commit]
        queue = [child for c in queue for child in tree.get(c, [])]

        while queue:
            current = queue.pop(0)
            visited.append(current)
            for child in tree.get(current, []):
                if len(child.parents) != 1:
                    queue.append(child)
                
        return visited

    def progress(self) -> CheckoutAndMergeResult:
        if self.wd.result_obj is BaseException:
            raise self.wd.result_obj

        repo_path = self.wd.result_obj
        if not isinstance(repo_path, str):
            raise BaseException(f"Unknown repo path {repo_path}")
        
        if len(self.env.branches) == 0:
            raise BaseException(f"Empty branches set")

        # Open the repository
        repo = git.Repo(repo_path)
        # Set user email and name for the repo
        with repo.config_writer() as cw:
            cw.set_value("user", "email", self.git_user_email)
            cw.set_value("user", "name", self.git_user_name)
        logger.info(f"Selected branches: {self.env.branches}")
        # Extract commit ids for the selected branches
        commit_ids: Dict[Commit, str] = {}
        for branch_pair in self.env.branches:
            branch_name, desired_commit = branch_pair
            if desired_commit == 'HEAD':
                commit = repo.commit(f'origin/{branch_name}')
            else:
                commit = repo.commit(desired_commit)
            commit_ids[commit] = branch_name

        logger.info(f"Commit ids for branches: {commit_ids}")

        tree = self._commits_tree(repo)

        merge_commit = [(c, self._find_merge_childs(tree, c)) for c in commit_ids.keys()]
        result = set(merge_commit[0][1])
        for c, l in merge_commit[1:]:
            result = set(result).intersection(set(l))
            if len(result) == 0:
                break

        if len(result) > 0:
            merge_commit = [c for c in merge_commit[0][1] if c in result][0]
            logger.info(f"Common commit found {merge_commit}")
        else:
            merge_commit = None
            logger.info(f"Common commit not found")

        sorted_commits = sorted(commit_ids.keys(), key=lambda x: x.hexsha)
        auto_branch_hash = hashlib.sha1(''.join([x.hexsha for x in sorted_commits]).encode()).hexdigest()
        auto_branch_name = f"auto/{auto_branch_hash}"
        version = '-'.join([x.hexsha[0:8] for x in sorted_commits])
        if merge_commit is not None:
            for head in repo.branches:
                if head.is_remote and head.commit.hexsha == merge_commit.hexsha:
                    logger.info(f"Merge commit {merge_commit} corresponds to branch {head}")
                    repo.git.checkout(head.name)
                    return CheckoutAndMergeResult(head.name, merge_commit.hexsha, version)


        if merge_commit is not None:
            repo.git.branch('-f', auto_branch_name, merge_commit.hexsha)
            repo.git.checkout(auto_branch_name)
            logger.info(f"Head is {repo.head.commit}")
            if self.push:
                repo.git.push('-f', 'origin', auto_branch_name)
                logger.info(f"Pushed {merge_commit} to {auto_branch_name}")
            return CheckoutAndMergeResult(auto_branch_name, merge_commit.hexsha, version)
        
        logger.info(f"Looking for existing auto branch: {auto_branch_name}")
        
        # Check if the auto branch already exists
        for remote_ref in repo.remotes.origin.refs:
            if remote_ref.name == f"origin/{auto_branch_name}":
                # Auto branch exists, fetch it
                logger.info(f"Found existing auto branch: {auto_branch_name}")
                repo.git.checkout(auto_branch_name)
                auto_branch_hash = repo.head.commit.hexsha
                
                return CheckoutAndMergeResult(auto_branch_name, auto_branch_hash, version)

        if auto_branch_name in repo.branches:
            repo.git.branch('-D', auto_branch_name)
        # Auto branch doesn't exist, create it
        logger.info(f"Creating new auto branch: {auto_branch_name}")
        
        commits = list(commit_ids.keys())
        repo.git.branch('-f', auto_branch_name,  commits[0].hexsha)
        repo.git.checkout(commits[0].hexsha)
        
        # Merge the rest of the branches
        for commit in commits[1:]:
            try:
                logger.info(f"Merging commit: {commit}")
                repo.git.merge(commit, '--no-ff')
            except git.GitCommandError as e:
                # Handle merge conflicts according to predefined rules
                # For now, we'll abort the merge and report failure
                repo.git.merge('--abort')
                error_message = f"Merge conflict when merging {commit}: {str(e)}"
                logger.error(error_message)
                
                raise BaseException(error_message)
        
        
        auto_branch_hash = repo.head.commit.hexsha
        if self.push:
            logger.info(f"Pushing {auto_branch_hash} to {auto_branch_name}")
            repo.git.push('-f', 'origin', auto_branch_name)
        return CheckoutAndMergeResult(auto_branch_name,auto_branch_hash, version)


from steps.docker import DockerSwarmCheckResult, DockerSwarmCheck

class GitUnmerge(AbstractStep[List[str]]):
    wd: GitClone

    def __init__(self, wd: GitClone,
                 check: DockerSwarmCheck,
                  **kwargs):
        super().__init__(**kwargs)
        self.wd = wd
        self.check = check

    def progress(self) -> List[str]:
        wd = self.wd.result
        deployState: Dict[str, DockerSwarmCheckResult] = self.check.result

        version = set([it.version for it in deployState.values()])
        if len(version) != 1:
            raise BaseException(f"Expected exactly one version, got: {version}")
        version = list(version)[0]
        repo = git.Repo(wd)
        if 'auto-' in version:
            version = version[len('auto-'):].split('-')

            commits = []
            for v in version:
                commit = repo.commit(v)
                # branches = [head.name for head in repo.heads if head.commit.hexsha == commit.hexsha]
                branches = [ref.name for ref in repo.remotes.origin.refs if ref.commit.hexsha == commit.hexsha]
                branches = [b[len('origin/'):] for b in branches if b.startswith('origin/') and not b.startswith('origin/HEAD')]
                
                # if len(branches) == 0 or branches[0].startswith('auto/'):
                #     # Find all parent commits of the given commit
                #     parents = [parent for parent in commit.parents]
                #     branches = [head.name for head in repo.heads for commit in parents if head.commit.hexsha == commit.hexsha]
                commits.append((commit.hexsha, branches))

            version = commits
        else:
            version = [version]
        return version


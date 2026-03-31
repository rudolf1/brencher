import hashlib
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
import traceback
from typing import List, Tuple, Set, Dict, Any, Mapping, runtime_checkable

import git
from enironment import AbstractStep
from git.objects import Commit

logger = logging.getLogger(__name__)


class GitClone(AbstractStep[str]):
	def __init__(self, repo_path: str | None = None, branchNamePrefix: str = "", credEnvPrefix: str = "GIT",
	             **kwargs: Any):
		super().__init__(**kwargs)
		self.repo_path = repo_path
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

		self.repo_path = self.repo_path or os.path.join(tempfile.gettempdir(),
		                                                f"{self.env.id}_{hashlib.sha1(self.env.repo.encode()).hexdigest()[:5]}")
		logger.info(f"Cloning repository {self.env.repo} to {self.repo_path}")
		os.makedirs(self.repo_path, exist_ok=True)
		try:
			if os.path.exists(os.path.join(self.repo_path, ".git")):
				logger.info(f"Repository already cloned at {self.repo_path}, fetching updates.")
				repo = git.Repo(self.repo_path)
				if repo.remotes.origin.url != self._get_auth_git_url(self.env.repo):
					repo.remotes.origin.set_url(self._get_auth_git_url(self.env.repo))
				result = repo.remotes.origin.fetch(prune=True)
				if not result or any(fetch_info.flags & fetch_info.ERROR for fetch_info in result):
					raise BaseException(f"Failed to fetch updates for {self.env.repo}")
			else:
				repo = git.Repo.init(self.repo_path)
				repo.remotes.append(repo.create_remote(
					'origin',
					self._get_auth_git_url(self.env.repo)
				))
				if self.branchNamePrefix != "":
					repo.config_writer().set_value('remote "origin"', "fetch",
					                               f"+refs/heads/{self.branchNamePrefix}/*:refs/remotes/origin/{self.branchNamePrefix}/*").release()
				repo.remotes.origin.fetch(prune=True)
				if not os.path.exists(os.path.join(self.repo_path, ".git")):
					raise BaseException(f"Failed to clone repository {self.env.repo} to {self.repo_path}")
		except BaseException as e:
			logger.error(f"Error during git clone/fetch, removing directory {self.repo_path}: {str(e)}")
			shutil.rmtree(self.repo_path)
			raise e
		return self.repo_path

	def get_branches(self) -> Dict[str, List[Any]]:
		repo = git.Repo(self.repo_path)
		result: Dict[str, List[Any]] = {}
		for ref in repo.refs:
			if ref.name.startswith('origin/') and not ref.name.startswith('origin/HEAD'):
				branch_name = ref.name[len('origin/'):]
				if not branch_name.startswith('auto/'):  # Skip auto branches
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


@dataclass
class CheckoutAndMergeResult:
	wd: str
	remote_branch_name: str | None
	commit_hash: str
	version: str


def _commits_childs(repo: git.Repo) -> Dict[Commit, List[Commit]]:
	childs: Dict[Commit, List[Commit]] = {}
	for c in list(repo.iter_commits('--all')):
		for p in c.parents:
			childs.setdefault(p, []).append(c)
	return childs


def ensure_clean(repo: git.Repo) -> None:
	if repo.is_dirty() or len(repo.untracked_files) > 0:
		raise BaseException(f"Changes in repo: U{repo.untracked_files}")


class CheckoutMerged(AbstractStep[CheckoutAndMergeResult]):
	wd: GitClone

	def __init__(self, wd: GitClone,
	             git_user_email: str,
	             git_user_name: str,
	             push: bool = True,
	             **kwargs: Any):
		super().__init__(**kwargs)
		self.wd = wd
		self.git_user_email = git_user_email
		self.git_user_name = git_user_name
		self.push = push

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

	def find_desired_commits(self, repo: git.Repo) -> Dict[Commit, str]:
		# Extract commit ids for the selected branches
		commit_ids: Dict[Commit, str] = {}
		for branch_pair in self.env.branches:
			try:
				branch_name, desired_commit = branch_pair
				if desired_commit == 'HEAD':
					commit = repo.commit(f'origin/{branch_name}')
				else:
					commit = repo.commit(desired_commit)
				commit_ids[commit] = branch_name
			except BaseException as e:
				stack = traceback.format_exception(type(e), e, e.__traceback__)
				logger.error(f"Error finding desired commits for branch {branch_pair}: {str(e)}\n{''.join(stack)}")
		return commit_ids

	def progress(self) -> CheckoutAndMergeResult:

		repo_path = self.wd.progress()

		# Open the repository
		repo = git.Repo(repo_path)
		# Set user email and name for the repo
		with repo.config_writer() as cw:
			cw.set_value("user", "email", self.git_user_email)
			cw.set_value("user", "name", self.git_user_name)

		if len(self.env.branches) == 0:
			raise BaseException(f"Empty branches set")

		logger.info(f"Selected branches: {self.env.branches}")

		commit_ids = self.find_desired_commits(repo)
		logger.info(f"Commit ids for branches: {commit_ids}")

		childs = _commits_childs(repo)

		def find_common_merge_commits() -> Set[Commit]:
			merge_commit: list[tuple[Commit, list[Commit]]] = [(c, self._find_merge_childs(childs, c)) for c in
			                                                   commit_ids.keys()]
			legal_merge_commits = [set(l) for c, l in merge_commit]
			result = legal_merge_commits[0]
			for l in legal_merge_commits[1:]:
				result = result.intersection(l)
			return result

		if len(commit_ids) == 1:
			commit_resulting = list(commit_ids.keys())[0]
			logger.info(f"Only one branch selected, using commit {commit_resulting.hexsha}")
		else:
			merge_commits = find_common_merge_commits()  # TODO There bugs here
			commit_resulting = None
			if len(merge_commits) > 0:
				commit_resulting = merge_commits.pop()
				logger.info(f"Common commit found {merge_commits}")

		if commit_resulting is None:
			logger.info(f"Merging commits")
			# Merge the rest of the branches
			commits = list(commit_ids.keys())
			repo.git.checkout(commits[0].hexsha, detach=True)
			ensure_clean(repo)
			for commit in commits[1:]:
				try:
					logger.info(f"Merging commit: {commit}")
					result = repo.git.merge(commit.hexsha)
					logger.info(result)
					ensure_clean(repo)
				except BaseException as e:
					# Handle merge conflicts according to predefined rules
					# For now, we'll abort the merge and report failure
					repo.git.merge('--abort')
					error_message = f"Merge conflict when merging {commit}: {str(e)}"
					logger.error(error_message)

					raise BaseException(error_message)
			commit_resulting = repo.head.commit

		repo.git.checkout(commit_resulting.hexsha, detach=True)
		ensure_clean(repo)
		remote_branch_name = None
		sorted_commits = sorted(commit_ids.keys(), key=lambda x: x.hexsha)
		version = '-'.join([x.hexsha[0:8] for x in sorted_commits])

		for ref in repo.refs:
			if ref.is_remote() and ref.commit == repo.head.commit and ref.name != 'origin/HEAD':
				logger.info(f"Merge commit {ref.commit} corresponds to branch {ref}")
				remote_branch_name = ref.name[len('origin/'):]
				break
		if self.push and remote_branch_name is None:
			auto_branch_hash = hashlib.sha1(''.join([x.hexsha for x in sorted_commits]).encode()).hexdigest()
			auto_branch_name = f"auto-{version}"

			logger.info(f"Pushing {repo.head.commit.hexsha} -> {auto_branch_name}")
			repo.git.push('-f', 'origin', f"HEAD:refs/heads/{auto_branch_name}")
			remote_branch_name = auto_branch_name

		return CheckoutAndMergeResult(
			wd=repo_path,
			remote_branch_name=remote_branch_name,
			commit_hash=repo.head.commit.hexsha,
			version=version
		)


from typing import Protocol, Any


@runtime_checkable
class HasVersion(Protocol):
	version: str


@dataclass
class GitUnmergeResult:
	branches: List[Tuple[str, str]]  # (branch_name, commit_hash) pairs
	columns: Dict[str, Dict[str, str]]  # column_name -> {branch_name: value}


class GitUnmerge(AbstractStep[GitUnmergeResult]):
	wd: GitClone

	def __init__(self, wd: GitClone,
	             check: AbstractStep[Mapping[str, HasVersion]],
	             **kwargs: Any):
		super().__init__(**kwargs)
		self.wd = wd
		self.check = check

	def progress(self) -> GitUnmergeResult:
		wd = self.wd.progress()
		deployState: Mapping[str, HasVersion] = self.check.progress()

		versions = set([it.version for it in deployState.values()])
		if len(versions) != 1:
			raise BaseException(f"Expected exactly one version, got: {versions}")

		version = list(versions)[0]
		if version is None:
			raise BaseException(f"Expected exactly one version, got: {versions}")
		repo = git.Repo(wd)
		childs: Dict[Commit, List[Commit]] | None = None
		if 'auto-' in version:
			version_parts = version[len('auto-'):].split('-')

			commits: List[Tuple[str, str]] = []
			for v in version_parts:
				commit = repo.commit(v)
				# branches = [head.name for head in repo.heads if head.commit.hexsha == commit.hexsha]
				branches = [ref.name for ref in repo.remotes.origin.refs if ref.commit.hexsha == commit.hexsha]
				branches = [b[len('origin/'):] for b in branches if
				            b.startswith('origin/') and not b.startswith('origin/HEAD')]

				if len(branches) == 0 or branches[0].startswith('auto/'):
					if childs is None:
						childs = _commits_childs(repo)
					commitsSet = set([commit])
					while len(commitsSet) > 0:
						current = commitsSet.pop()
						for child in childs.get(current, []):
							branches = [ref.name for ref in repo.remotes.origin.refs if
							            ref.commit.hexsha == child.hexsha]
							branches = [b[len('origin/'):] for b in branches if
							            b.startswith('origin/') and not b.startswith('origin/HEAD')]

							if len(branches) > 0:
								commitsSet = set()
							else:
								commitsSet.add(child)
				for b in branches:
					commits.append((b, commit.hexsha))

			if len(commits) == 0:
				raise BaseException(f"Unable to unmerge version: {version}")

			deployed_col: Dict[str, str] = {b: c[:8] for b, c in commits}
			return GitUnmergeResult(
				branches=commits,
				columns={"Deployed": deployed_col},
			)
		else:
			raise BaseException(f"Version format not recognized: {version}")

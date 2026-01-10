from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class Environment:
    id: str
    branches: List[Tuple[str, str]]  # List of [branch_name, desired_commit] pairs
    dry: bool
    repo: str # git repo
    # pipeline: List[AbstractStep]

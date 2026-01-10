from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple, Callable

@dataclass
class Environment:
    id: str
    branches: List[Tuple[str, str]]  # List of [branch_name, desired_commit] pairs
    dry: bool
    repo: str # git repo
    # pipeline: List[AbstractStep]

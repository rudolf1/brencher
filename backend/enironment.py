from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from steps.step import AbstractStep

@dataclass
class Environment:
    id: str
    branches: List[Tuple[str, str]]
    state: str  # 'Active' or 'Pause'
    repo: str # git repo
    pipeline: Callable[[Any], List[AbstractStep]]

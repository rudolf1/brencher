from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple, Callable

@dataclass
class Environment:
    id: str
    branches: List[str]
    dry: bool
    repo: str # git repo
    # pipeline: List[AbstractStep]

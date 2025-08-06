from dataclasses import dataclass
from typing import Optional

@dataclass
class CheckoutMergedResult:
    branch_name: Optional[str] = None
    commit_hash: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

class CheckoutMerged:
    def process(self, clone_result, branches):
        # Implement the logic for checking out merged branches here
        # Return a CheckoutMergedResult instance
        pass
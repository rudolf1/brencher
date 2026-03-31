# Add backend to path so we can import modules
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
	sys.path.insert(0, str(backend_path))

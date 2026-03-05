"""
Pytest configuration and shared fixtures for integration tests.

This file configures the Python path to allow importing backend modules
and provides shared fixtures for all tests.
"""
import sys
from pathlib import Path

# Add backend to path so we can import modules
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

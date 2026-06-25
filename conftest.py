"""Make the project root importable when tests run via a bare ``pytest`` call.

The test suite imports top-level modules (e.g. ``from config import ...``).
Running ``pytest tests/`` (as CI does) does not put the repository root on
``sys.path``, unlike ``python -m pytest``. This conftest inserts the root
explicitly so tests import the same modules under both invocations.
"""
import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# conftest.py
import sys
from pathlib import Path

# Append the directory above "src" to the PYTHONPATH
# This allows tests to import from src.lib.core
sys.path.append(str(Path(__file__).resolve().parent.parent))

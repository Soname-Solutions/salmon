# conftest.py
import sys
from pathlib import Path
import os

# Append the directory above "src" to the PYTHONPATH
# This allows tests to import from src.lib.core
parent_folder = str(Path(__file__).resolve().parent.parent)
lib_path = os.path.join(parent_folder, "src")
sys.path.append(lib_path)

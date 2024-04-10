# conftest.py
import sys
from pathlib import Path
import os
import pytest

# Append the directory above "src" to the PYTHONPATH
# This allows tests to import from src.lib.core
parent_folder = str(Path(__file__).resolve().parent.parent)
lib_path = os.path.join(parent_folder, "src")
sys.path.append(lib_path)

@pytest.fixture(scope='session')
def config_path():    
    current_dir = Path(__file__).parent
    file_path = current_dir / "../config/settings/"    
    return file_path

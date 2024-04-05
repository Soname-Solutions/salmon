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

from lib.settings import Settings

def pytest_addoption(parser):
    parser.addoption("--stage-name", action="store")

@pytest.fixture(scope='session')
def config_path():    
    current_dir = Path(__file__).parent
    file_path = current_dir / "../config/settings/"    
    return file_path

@pytest.fixture(scope='session')
def stage_name(request):
    # requires stage-name parameter to be given, like:
    # pytest -q -s --stage-name devam
    name_value = request.config.option.stage_name

    if name_value is None:
        raise Exception("Please specify a stage name using --stage-name")
    else:
        print(f"Using stage name: {name_value}")
    
    return name_value
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


@pytest.fixture(scope="session")
def config_path():
    current_dir = Path(__file__).parent
    file_path = current_dir / "../config/settings/"
    return file_path


@pytest.fixture(scope="session")
def aws_props_init(config_path):
    # Inits AWS acc id and region (from local settings -> tooling env)
    print(config_path)
    settings = Settings.from_file_path(config_path)
    account_id, region = settings.get_tooling_account_props()

    return (account_id, region)


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["MOTO_S3_CUSTOM_ENDPOINTS"] = (
        "http://custom.internal.endpoint,http://custom.other.endpoint"
    )

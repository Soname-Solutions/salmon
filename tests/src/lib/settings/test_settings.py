import pytest
import os
import boto3
import json
from moto import mock_aws

from lib.settings import Settings

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
MOCKED_S3_BUCKET_NAME = "mocked_s3_config_bucket"

TOOLING_ACCOUNT_ID = "1234567890"
TOOLING_REGION = "us-east-1"

##############################################################################

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'    

@pytest.fixture
def s3_setup(aws_credentials):
    with mock_aws():
        conn = boto3.client('s3', region_name='us-east-1')
        conn.create_bucket(Bucket=MOCKED_S3_BUCKET_NAME)
        
        # Path to your test configuration
        config_folder = os.path.join(CURRENT_FOLDER, "test_configs/config1/")
        
        # Upload files to the mocked S3 bucket
        for filename in os.listdir(config_folder):
            file_path = os.path.join(config_folder, filename)
            with open(file_path, 'rb') as file_data:
                conn.upload_fileobj(file_data, MOCKED_S3_BUCKET_NAME, filename)
        
        yield    

##############################################################################

# testing reading config from local path (with minimal checks)
def test_read_from_path():
    config_path = os.path.join(CURRENT_FOLDER , "test_configs/config1/")
    settings = Settings.from_file_path(config_path)

    tooling_account_props = settings.get_tooling_account_props()

    assert tooling_account_props == (TOOLING_ACCOUNT_ID, TOOLING_REGION), f"Tooling account properties doesn't match"


# testing reading config from mocked S3 bucket (with minimal checks)
def test_from_s3_path(s3_setup):
    config_path = f"s3://{MOCKED_S3_BUCKET_NAME}/"
    settings = Settings.from_s3_path(config_path)
    
    # Example of asserting the properties of the tooling account
    # Adjust the expected values according to the actual settings in 'config1'
    tooling_account_props = settings.get_tooling_account_props()
    assert tooling_account_props == (TOOLING_ACCOUNT_ID, TOOLING_REGION), f"Tooling account properties doesn't match"
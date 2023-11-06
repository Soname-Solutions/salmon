import pytest
from botocore.exceptions import ClientError
from unittest.mock import MagicMock
from src.s3_manager import S3Manager


class TestS3Manager:
    @pytest.fixture(scope="class")
    def s3_manager(self):
        return S3Manager()

    def test_read_settings_file_successful(self, s3_manager):
        bucket_name = "test_bucket"
        file_name = "test_file"
        content = "Sample content for the file"

        # Mocking the S3 client's get_object method
        expected_response = {
            "Body": MagicMock(read=MagicMock(return_value=content.encode("utf-8")))
        }
        s3_manager.s3_client.get_object = MagicMock(return_value=expected_response)

        downloaded_content = s3_manager.read_settings_file(bucket_name, file_name)
        assert downloaded_content == content

    def test_read_settings_file_failure(self, s3_manager):
        bucket_name = "test_bucket"
        file_name = "non_existent_file"

        # Mocking the S3 client's get_object method to raise an exception
        s3_manager.s3_client.get_object = MagicMock(
            side_effect=ClientError({"Error": {}}, "operation_name")
        )

        with pytest.raises(Exception) as exc_info:
            s3_manager.read_settings_file(bucket_name, file_name)

        assert "Error reading settings file" in str(exc_info.value)

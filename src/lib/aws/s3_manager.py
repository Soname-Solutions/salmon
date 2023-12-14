import boto3
from botocore.exceptions import ClientError
from urllib.parse import urlparse


class S3ManagerReadException(Exception):
    """Exception raised for errors encountered while reading files using S3Manager."""

    pass


class S3Manager:
    """Manages interactions with Amazon S3.

    This class encapsulates methods for reading files from an S3 bucket.

    Attributes:
        s3_client: Boto3 S3 client for AWS interactions.

    Methods:
        read_settings_file: Reads file from the specified S3 bucket.

    Raises:
        S3ManagerReadException: If there's an error reading settings file.

    """

    def __init__(self, s3_client: boto3.client = None):
        """S3Manager class constructor.

        Args:
            s3_client (boto3.client): Custom s3 client.

        """
        self.s3_client = boto3.client("s3") if s3_client is None else s3_client

    def read_file(self, s3_path: str) -> str:
        """Read a file from the specified S3 bucket.

        Args:
            s3_path (str): Full S3 path (e.g. s3://your_bucket_name/path/to/your/object/file.txt).

        Returns:
            str: The content of the file as a string or None if an error occurs.

        """
        try:
            s3_path_parts = urlparse(s3_path, allow_fragments=False)
            response = self.s3_client.get_object(
                Bucket=s3_path_parts.netloc, Key=s3_path_parts.path.lstrip("/")
            )
            settings_data = response["Body"].read().decode("utf-8")
            return settings_data
        except ClientError as e:
            if e.response["Error"]["Code"] in ["NoSuchKey", "AccessDenied"]:
                raise FileNotFoundError(f"File not found: {s3_path}") from e
            else:
                error_message = f"Error reading settings file from '{s3_path}': {e}"
                raise S3ManagerReadException(error_message)

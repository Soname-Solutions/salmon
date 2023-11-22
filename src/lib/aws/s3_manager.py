import boto3


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

    def read_file(self, bucket_name: str, file_name: str) -> str:
        """Read a file from the specified S3 bucket.

        Args:
            bucket_name (str): The name of the S3 bucket.
            file_name (str): The name of the file to read.

        Returns:
            str: The content of the file as a string or None if an error occurs.

        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=file_name)
            settings_data = response["Body"].read().decode("utf-8")
            return settings_data
        except Exception as e:
            error_message = f"Error reading settings file {file_name}: {e}"
            raise S3ManagerReadException(error_message)

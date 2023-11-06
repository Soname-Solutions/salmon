import boto3


class S3Manager:
    """Manages interactions with Amazon S3.

    This class encapsulates methods for downloading files from an S3 bucket.

    Attributes:
        s3_client: Boto3 S3 client for AWS interactions.

    Methods:
        download_settings_file: Downloads a file from the specified S3 bucket.

    Raises:
        Exception: If there's an error downloading settings file.

    """

    def __init__(self):
        self.s3_client = boto3.client("s3")

    def read_settings_file(self, bucket_name: str, file_name: str) -> str:
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
            raise Exception(f"Error reading settings file {file_name} : {e}")

import json
import boto3
from botocore.exceptions import ClientError
from typing import Dict


class SecretManagerClientException(Exception):
    """Error while retrieving a secret from AWS Secrets Manager."""

    pass


class SecretManager:
    """Manages interactions with AWS Secrets Manager."""

    def __init__(self, secret_client=None) -> None:
        """Initiate class SecretManager.

        Args:
            secret_client: Boto3 SES client for AWS interactions.
        """
        self._secret_client = (
            boto3.client(service_name="secretsmanager")
            if secret_client is None
            else secret_client
        )

    def get_secret(self, secret_name: str) -> Dict[str, str]:
        """Get a secret from AWS Secrets Manager.

        Args:
            secret_name (str): Secret name.
        """
        try:
            get_secret_value_response = self._secret_client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise SecretManagerClientException(
                f"Error during retrieving a secret from AWS Secrets Manager: {str(e)}."
            ) from e

        return json.loads(get_secret_value_response["SecretString"])

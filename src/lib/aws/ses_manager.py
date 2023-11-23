import boto3
import botocore
from typing import List


class AwsSesRawEmailSenderException(Exception):
    """Error while sending a message via AWS SES."""

    pass


class AwsSesManager:
    """Manages interactions with Amazon SES."""

    """

    Methods:
        read_settings_file: Reads file from the specified S3 bucket.

    """

    def __init__(self, ses_client=None) -> None:
        """Initiate class AwsSesManager.

        Args:
            ses_client: Boto3 SES client for AWS interactions.
        """
        self._ses_client = boto3.client("ses") if ses_client is None else ses_client

    def _get_identities(self, next_token: str = None) -> List[str]:
        """Get all identities from AWS SES"""
        kwargs = {"IdentityType": "EmailAddress", "MaxItems": 1000}

        if next_token is not None:
            kwargs.update({"NextToken": next_token})

        response = self._ses_client.list_identities(**kwargs)

        identities = response["Identities"]
        next_token = response.get("NextToken")

        if next_token is None:
            return identities
        else:
            return identities + self._get_identities(next_token)

    def _get_verification_status(self, identity: str) -> str:
        """Get verification status for identity."""
        return self._ses_client.get_identity_verification_attributes(
            Identities=[identity]
        )["VerificationAttributes"][identity]["VerificationStatus"]

    def is_identity_verified(self, identity: str) -> bool:
        """Check if identity is verified."""
        return self._get_verification_status(identity) == "Success"

    def get_verified_identities(self) -> List[str]:
        """Get verified identities."""
        return [
            identity
            for identity in self._get_identities()
            if self.is_identity_verified(identity)
        ]

    def send_raw_email(self, message: str) -> None:
        """Send a message via AWS SES.

        Args:
            message (str): Message to send
        """
        try:
            self._ses_client.send_raw_email(RawMessage={"Data": message})
        except botocore.exceptions.ClientError as ex:
            raise AwsSesRawEmailSenderException(
                f"Error during sending email to AWS SES: {str(ex)}."
            ) from ex

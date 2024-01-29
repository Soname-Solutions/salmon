import boto3

from .aws_naming import AWSNaming
from .sts_manager import StsManager


class Boto3ClientCreatorException(Exception):
    """Exception raised for errors encountered while creating of boto3 client."""

    pass


class Boto3ClientCreator:
    """This class creates boto3 client."""

    def __init__(self, account_id: str, region: str, iam_role_name: str = None):
        self.account_id = account_id
        self.region = region
        self.iam_role_name = iam_role_name

    def get_client(self, aws_client_name):
        if self.iam_role_name:
            sts_client = boto3.client("sts")
            sts_manager = StsManager(sts_client)
            extract_metrics_role_arn = AWSNaming.Arn_IAMRole(
                None, self.account_id, self.iam_role_name
            )

            try:
                client = sts_manager.get_client_via_assumed_role(
                    aws_client_name=aws_client_name,
                    via_assume_role_arn=extract_metrics_role_arn,
                    region=self.region,
                )
                return client
            except Exception as ex:
                raise Boto3ClientCreatorException(
                    f"Error while creating boto3 client: {str(ex)}"
                )
        else:
            return boto3.client(aws_client_name)

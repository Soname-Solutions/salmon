import boto3


class StsManagerException(Exception):
    """Exception raised for errors encountered while running STS client methods."""

    pass


class StsManager:
    def __init__(self, sts_client=None):
        self.sts_client = boto3.client("sts") if sts_client is None else sts_client

    def assume_role(self, role_arn, role_session_name="default_name"):
        try:
            response = self.sts_client.assume_role(
                RoleArn=role_arn, RoleSessionName=role_session_name
            )

            return response["Credentials"]
        except Exception as e:
            error_message = f"Error assuming role {role_arn}: {e}"
            raise StsManagerException(error_message)

    # retrieves temporary credentials via assuming role (cross-account)
    # creates and returns boto3 client for requested services - using credentials from assume role action
    def get_client_via_assumed_role(self, aws_client_name, via_assume_role_arn, region):
        try:
            credentials = self.assume_role(via_assume_role_arn)

            ACCESS_KEY = credentials["AccessKeyId"]
            SECRET_KEY = credentials["SecretAccessKey"]
            SESSION_TOKEN = credentials["SessionToken"]

            outp_client = boto3.client(
                aws_client_name,
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
                aws_session_token=SESSION_TOKEN,
                region_name=region,
            )

            return outp_client
        except Exception as e:
            error_message = f"Error creating client: {e}"
            raise StsManagerException(error_message)

    # Returns AWS account ID
    def get_account_id(self):
        try:
            response = self.sts_client.get_caller_identity()
            return response["Account"]
        except Exception as e:
            error_message = f"Error retrieving AWS account ID: {e}"
            raise StsManagerException(error_message)

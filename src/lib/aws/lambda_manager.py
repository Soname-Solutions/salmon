import boto3


class LambdaManagerException(Exception):
    """Exception raised for errors encountered while running Lambda client methods."""

    pass


class LambdaManager:
    def __init__(self, lambda_client=None):
        self.lambda_client = (
            boto3.client("lambda") if lambda_client is None else lambda_client
        )

    def get_all_names(self, **kwargs):
        try:
            response = self.lambda_client.list_functions()
            return [res["FunctionName"] for res in response.get("Functions")]

        except Exception as e:
            error_message = f"Error getting list of lambda functions : {e}"
            raise LambdaManagerException(error_message)

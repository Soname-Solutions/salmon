import boto3


class StepFunctionsManagerException(Exception):
    """Exception raised for errors encountered while running Stepfunctions client methods."""

    pass


class StepFunctionsManager:
    def __init__(self, sf_client=None):
        self.sf_client = (
            boto3.client("stepfunctions") if sf_client is None else sf_client
        )

    def get_all_names(self, **kwargs):
        try:
            response = self.sf_client.list_state_machines()
            return [res["name"] for res in response.get("stateMachines")]

        except Exception as e:
            error_message = f"Error getting list of step functions : {e}"
            raise StepFunctionsManagerException(error_message)

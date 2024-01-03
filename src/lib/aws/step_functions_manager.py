import boto3
from datetime import datetime

from pydantic import BaseModel
from typing import Optional


class ExecutionData(BaseModel):
    executionArn: str
    stateMachineArn: str
    name: str
    status: str
    startDate: datetime
    stopDate: datetime

    @property
    def IsSuccess(self) -> bool:
        return self.status in StepFunctionsManager.STATES_SUCCESS

    @property
    def IsFailure(self) -> bool:
        return self.status in StepFunctionsManager.STATES_FAILURE

    @property
    def Duration(self) -> float:
        return (self.stopDate - self.startDate).total_seconds()


class StepFunctionExecutionsData(BaseModel):
    executions: list[ExecutionData]
    nextToken: Optional[str]


class StepFunctionsManagerException(Exception):
    """Exception raised for errors encountered while running Stepfunctions client methods."""

    pass


class StepFunctionsManager:
    STATES_SUCCESS = ["SUCCEEDED"]
    STATES_FAILURE = ["FAILED", "ABORTED", "TIMED_OUT"]
    # FYI: all states = 'RUNNING'|'SUCCEEDED'|'FAILED'|'TIMED_OUT'|'ABORTED'|'PENDING_REDRIVE'

    @classmethod
    def is_final_state(cls, state: str) -> bool:
        return state in cls.STATES_SUCCESS or state in cls.STATES_FAILURE

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

    def get_step_function_arn_by_name(self, step_function_name):
        """
        Get the ARN of a specific AWS Step Function.

        :param step_function_name: Name of the Step Function state machine.
        :return: ARN of the Step Function state machine.
        """
        sf_client = self.sf_client

        try:
            response = sf_client.list_state_machines()
            state_machines = response["stateMachines"]

            for state_machine in state_machines:
                if state_machine["name"] == step_function_name:
                    return state_machine["stateMachineArn"]

            return None
        except Exception as e:
            error_message = f"Error getting step function ARN by name: {e}"
            raise StepFunctionsManagerException(error_message)

    def get_step_function_executions(
        self, step_function_name: str, since_time: datetime
    ) -> list[ExecutionData]:
        try:
            state_machine_arn = self.get_step_function_arn_by_name(step_function_name)
            response = self.sf_client.list_executions(
                stateMachineArn=state_machine_arn
            )

            step_function_executions_data = StepFunctionExecutionsData(**response)
            outp = [
                x
                for x in step_function_executions_data.executions
                if x.startDate > since_time
            ]

            return outp

        except Exception as e:
            error_message = f"Error getting step function executions: {e}"
            raise StepFunctionsManagerException(error_message)

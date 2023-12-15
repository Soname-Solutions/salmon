from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from lib.aws.step_functions_manager import StepFunctionsManager
import dateutil.tz

def list_step_function_executions(state_machine_arn):
    """
    List executions of a specific AWS Step Function.

    :param state_machine_arn: ARN of the Step Function state machine.
    :return: List of executions.
    """
    # Create a Step Functions client
    sf_client = boto3.client("stepfunctions")

    try:
        response = sf_client.list_executions(stateMachineArn=state_machine_arn)
        executions = response["executions"]

        for execution in executions:
            print(f"Execution ARN: {execution['executionArn']}")
            print(f"Status: {execution['status']}")
            print(f"Start Date: {execution['startDate']}")
            if "stopDate" in execution:
                print(f"Stop Date: {execution['stopDate']}")
            print("------")

        return executions
    except ClientError as e:
        print(f"An error occurred: {e}")
        return []


# # Example usage
# state_machine_arn = 'arn:aws:states:region:account-id:stateMachine:yourStateMachineName'
# list_step_function_executions(state_machine_arn)

step_functions_client = boto3.client("stepfunctions")

man = StepFunctionsManager(step_functions_client)

step_function_name = "stepfunction-salmonts-sample-dev"

since_time = datetime.now() - timedelta(hours=5)
utc_tz = dateutil.tz.gettz('UTC')
since_time = since_time.replace(tzinfo=utc_tz)

       

response = man.get_step_function_executions(step_function_name, since_time=since_time)

print(len(response))
print(response)

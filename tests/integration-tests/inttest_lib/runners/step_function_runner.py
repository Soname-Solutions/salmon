import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

from lib.aws.step_functions_manager import StepFunctionsManager


class StepFunctionRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("stepfunctions", region_name=region_name)
        self.sfn_runs = {}
        self.sfn_manager = StepFunctionsManager(self.client)

    def initiate(self):
        for sfn_name in self.resource_names:
            arn = self.sfn_manager.get_step_function_arn_by_name(sfn_name)
            response = self.client.start_execution(stateMachineArn=arn, input="{}")
            self.sfn_runs[sfn_name] = response["executionArn"]
            print(
                f"Started Step Function {sfn_name} with execution ARN {response['executionArn']}"
            )

    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for sfn_name, execution_arn in self.sfn_runs.items():
                response = self.client.describe_execution(executionArn=execution_arn)
                status = response["status"]
                print(
                    f"Step Function {sfn_name} with execution ARN {execution_arn} is in state {status}"
                )
                if not (StepFunctionsManager.is_final_state(status)):
                    all_completed = False

            if all_completed:
                break

            time.sleep(
                poll_interval
            )  # Wait for the specified poll interval before checking again

        print("All Step Function executions have completed.")

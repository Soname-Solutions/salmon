import boto3
import time
import json

from inttest_lib.runners.base_resource_runner import BaseResourceRunner
from lib.aws.cloudwatch_manager import CloudWatchManager, CloudWatchManagerException
from lib.aws.lambda_manager import LambdaManager
from lib.aws.aws_naming import AWSNaming


class LambdaFunctionRunnerException(Exception):
    pass


class LambdaFunctionRunner(BaseResourceRunner):
    def __init__(self, resources_data, region_name, stack_obj):
        super().__init__([], region_name)
        self.client = boto3.client("lambda", region_name=region_name)
        self.resources_data = resources_data
        self.stack_obj = stack_obj
        self.lambda_manager = LambdaManager(
            boto3.client("lambda", region_name=region_name)
        )
        self.logs_manager = CloudWatchManager(
            boto3.client("logs", region_name=region_name)
        )
        self.function_runs = {}

    def initiate(self):
        self.start_time = int(time.time() * 1000)

        for lambda_meaning, retry_attempts in self.resources_data.items():
            lambda_function_name = AWSNaming.LambdaFunction(
                self.stack_obj, lambda_meaning
            )
            # Walkaround for the case when LambdaFunction is launched for the first time, CW LogGroup
            # might be created with timestamp later than first CW first records
            # it prevent "await" method to find run INIT and, potentially, END records in logs
            # so we create log group explicitly beforehand
            log_group_name = self.lambda_manager.get_log_group(lambda_function_name)
            if not (self.logs_manager.log_group_exists(log_group_name)):
                print(
                    f"Creating log group {log_group_name} as it hasn't been created yet."
                )
                self.logs_manager.create_log_group(log_group_name)

            request_id = self._invoke_lambda_async(lambda_function_name)
            self.function_runs[lambda_function_name] = {
                "request_id": request_id,
                "retry_attempts": retry_attempts,
            }
            print(f"Invoked {lambda_function_name} with request ID {request_id}")

    def _invoke_lambda_async(
        self, lambda_function_name: str, payload: dict = {}
    ) -> dict:
        """
        return lambda's execution RequestId
        """
        try:
            response = self.client.invoke(
                FunctionName=lambda_function_name,
                InvocationType="Event",  # Asynchronous invocation
                Payload=json.dumps(payload),
            )
            request_id = response.get("ResponseMetadata", {}).get("RequestId")
            if not request_id:
                raise LambdaFunctionRunnerException(
                    f"RequestId not found in response for {lambda_function_name}"
                )
            return request_id
        except Exception as e:
            error_message = f"Error invoking lambda function {lambda_function_name} asynchronously: {e}"
            raise LambdaFunctionRunnerException(error_message)

    def await_completion(self, poll_interval=10):
        while True:
            time.sleep(poll_interval)
            all_completed = True
            for lambda_function_name, run_data in self.function_runs.items():
                if not self._is_lambda_completed(lambda_function_name, run_data):
                    all_completed = False
                    break
            if all_completed:
                print("All Lambda functions have completed.")
                return
            print("Waiting for Lambda functions to complete...")

    def _is_lambda_completed(self, lambda_function_name, run_data):
        log_group_name = f"/aws/lambda/{lambda_function_name}"
        request_id = run_data["request_id"]
        retry_attempts = run_data["retry_attempts"]
        expected_runs = retry_attempts + 1
        query_string = f"fields @timestamp, @message | filter @message like /END RequestId: {request_id}/"

        try:
            results = self.logs_manager.query_logs(
                log_group_name=log_group_name,
                query_string=query_string,
                start_time=self.start_time,
                end_time=int(time.time() * 1000),
            )

            if results and len(results) == expected_runs:
                print(
                    f"Lambda function {lambda_function_name} with request ID {request_id} and {retry_attempts} retry attempt(s) has completed."
                )
                return True
        except CloudWatchManagerException as e:
            error_message = f"Error checking CloudWatch logs for lambda function {lambda_function_name}: {e}"
            raise LambdaFunctionRunnerException(error_message)
        return False

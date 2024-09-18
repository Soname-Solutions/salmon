import boto3
import time
import json
from datetime import datetime, timedelta

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

from lib.aws.cloudwatch_manager import CloudWatchManager, CloudWatchManagerException
from lib.core.datetime_utils import datetime_to_epoch_milliseconds


class LambdaFunctionRunnerException(Exception):
    pass


class LambdaFunctionRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("lambda", region_name=region_name)
        self.logs_manager = CloudWatchManager(
            boto3.client("logs", region_name=region_name)
        )
        self.function_runs = {}

    def initiate(self):
        for lambda_function_name in self.resource_names:
            request_id = self._invoke_lambda_async(lambda_function_name)
            self.function_runs[lambda_function_name] = request_id
            print(
                f"Invoked {lambda_function_name} with request ID {self.function_runs[lambda_function_name]}"
            )

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
        start_time = datetime.now() - timedelta(
            seconds=poll_interval
        )  # - poll_sec for safety (if lambda executes too quickly)
        while True:
            time.sleep(poll_interval)
            all_completed = True
            for lambda_function_name, request_id in self.function_runs.items():
                if not self._is_lambda_completed(
                    lambda_function_name, request_id, start_time
                ):
                    all_completed = False
                    break
            if all_completed:
                print("All Lambda functions have completed.")
                return
            print("Waiting for Lambda functions to complete...")

    def _is_lambda_completed(self, lambda_function_name, request_id, start_time):
        log_group_name = f"/aws/lambda/{lambda_function_name}"
        query_string = f"fields @timestamp, @message | filter @message like /END RequestId: {request_id}/"

        try:
            query_start_time = int(datetime_to_epoch_milliseconds(start_time))
            query_end_time = int(datetime_to_epoch_milliseconds(datetime.now()))
            results = self.logs_manager.query_logs(
                log_group_name, query_string, query_start_time, query_end_time
            )
            if results:
                print(
                    f"Lambda function {lambda_function_name} with request ID {request_id} has completed."
                )
                return True
        except CloudWatchManagerException as e:
            error_message = f"Error checking CloudWatch logs for lambda function {lambda_function_name}: {e}"
            raise LambdaFunctionRunnerException(error_message)
        return False

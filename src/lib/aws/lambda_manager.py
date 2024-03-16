import re
import boto3
from datetime import datetime

from pydantic import BaseModel
from typing import Optional

from .cloudwatch_manager import CloudWatchManager
from lib.core.datetime_utils import str_utc_datetime_to_datetime


###########################################################
class LogEntry(BaseModel):
    name: str
    timestamp: datetime
    message: str
    requestId: Optional[str]

    @property
    def IsReportEvent(self) -> bool:
        return LambdaManager.MESSAGE_PART_REPORT in self.message

    @property
    def IsErrorEvent(self) -> bool:
        return LambdaManager.MESSAGE_PART_ERROR in self.message

    @property
    def Duration(self) -> float:
        duration_match = re.search(r"Duration: ([0-9.]+) ms", self.message)
        return float(duration_match.group(1)) if duration_match else 0

    @property
    def BilledDuration(self) -> float:
        billed_duration_match = re.search(r"Billed Duration: (\d+) ms", self.message)
        return float(billed_duration_match.group(1)) if billed_duration_match else 0

    @property
    def MemorySize(self) -> float:
        memory_size_match = re.search(r"Memory Size: (\d+) MB", self.message)
        return float(memory_size_match.group(1)) if memory_size_match else 0

    @property
    def MaxMemoryUsed(self) -> float:
        max_memory_used_match = re.search(r"Max Memory Used: (\d+) MB", self.message)
        return float(max_memory_used_match.group(1)) if max_memory_used_match else 0


###########################################################


class LambdaManagerException(Exception):
    """Exception raised for errors encountered while running Lambda client methods."""

    pass


class LambdaManager:
    MESSAGE_PART_REPORT = "REPORT RequestId:"
    MESSAGE_PART_ERROR = "[ERROR]"

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

    def get_log_group(self, lambda_function_name: str) -> str:
        response = self.lambda_client.get_function(FunctionName=lambda_function_name)[
            "Configuration"
        ]
        return response.get("LoggingConfig", {}).get(
            "LogGroup", f"/aws/lambda/{lambda_function_name}"
        )

    def get_lambda_logs(
        self,
        cloudwatch_manager: CloudWatchManager,
        function_name: str,
        since_time: datetime,
    ) -> list[LogEntry]:
        """Get lambda logs from CloudWatch

        Example response from CloudWatch:
            [
                [
                    {'field': '@timestamp', 'value': '2024-01-19 08:36:56.462'},
                    {'field': '@message', 'value': 'REPORT RequestId: 5e844c16-4356-4c04-a266-c92d590415c3\tDuration: 4770.03 ms\tBilled Duration: 4771 ms\tMemory Size: 128 MB\tMax Memory Used: 102 MB\t\n'},
                    {'field': '@requestId', 'value': '5e844c16-4356-4c04-a266-c92d590415c3'},
                    {'field': '@ptr', 'value': 'Cn0KQAo8NDA1M...'}
                ],
                [
                    {'field': '@timestamp', 'value': '2024-01-19 08:36:56.444'},
                    {'field': '@message', 'value': '[ERROR] Exception: ...'},
                    {'field': '@ptr', 'value': 'Cn0KQAo8NDA1M...'}
                ],
                ...
            ]
        """

        query_string = f"""
            fields @timestamp, @message, @requestId
            | filter @message like '{self.MESSAGE_PART_REPORT}' or @message like '{self.MESSAGE_PART_ERROR}'
            | sort @timestamp desc
        """

        try:
            lambda_logs = cloudwatch_manager.query_logs(
                log_group_name=self.get_log_group(function_name),
                query_string=query_string,
                start_time=since_time,
                end_time=datetime.now(),
            )
            lambda_function_log_data = []
            for log_entry_data in lambda_logs:
                log_entry = LogEntry(
                    name=function_name,
                    timestamp=str_utc_datetime_to_datetime(log_entry_data[0]["value"]),
                    message=log_entry_data[1]["value"],
                    requestId=log_entry_data[2]["value"]
                    if log_entry_data[2]["field"] == "@requestId"
                    else None,
                )
                lambda_function_log_data.append(log_entry)
            return lambda_function_log_data
        except Exception as e:
            error_message = f"Error getting lambda function log data: {e}"
            raise LambdaManagerException(error_message)

import re
import boto3
from datetime import datetime, timedelta

from pydantic import BaseModel
from typing import List, Dict, Optional

from .cloudwatch_manager import CloudWatchManager
from lib.core.datetime_utils import (
    datetime_to_epoch_milliseconds,
    str_utc_datetime_to_datetime,
)


###########################################################


class LogEntry(BaseModel):
    LambdaName: str
    LogStream: str
    RequestId: Optional[str]
    Status: Optional[str] = None
    Report: Optional[str] = None
    Errors: Optional[List[str]] = []
    StartedOn: Optional[datetime] = None
    CompletedOn: Optional[datetime] = None

    @property
    def IsFinalState(self) -> bool:
        return bool(self.StartedOn and self.Report)

    @property
    def IsSuccess(self) -> bool:
        return self.Status in LambdaManager.LAMBDA_SUCCESS_STATE

    @property
    def IsFailure(self) -> bool:
        return self.Status in LambdaManager.LAMBDA_FAILURE_STATE

    def _extract_value(self, pattern: str) -> float:
        if self.Report:
            match = re.search(pattern, self.Report)
            if match:
                return float(match.group(1))
        return 0.0

    @property
    def Duration(self) -> float:
        return self._extract_value(r"Duration: ([0-9.]+) ms")

    @property
    def BilledDuration(self) -> float:
        return self._extract_value(r"Billed Duration: (\d+) ms")

    @property
    def MemorySize(self) -> float:
        return self._extract_value(r"Memory Size: (\d+) MB")

    @property
    def MaxMemoryUsed(self) -> float:
        return self._extract_value(r"Max Memory Used: (\d+) MB")

    @property
    def ErrorString(self) -> str:
        if not self.Errors:
            return None

        error_string = "; ".join(self.Errors)
        return error_string[:100] + "..." if len(error_string) > 100 else error_string


###########################################################


class LambdaManagerException(Exception):
    """Exception raised for errors encountered while running Lambda client methods."""

    pass


class LambdaManager:
    MESSAGE_PART_START = "START"
    MESSAGE_PART_END = "END"
    MESSAGE_PART_REPORT = "REPORT RequestId:"
    MESSAGE_PART_ERROR = "[ERROR]"
    LAMBDA_SUCCESS_STATE = "SUCCEEDED"
    LAMBDA_FAILURE_STATE = "FAILED"
    LAMBDA_RUNNING_STATE = "RUNNING"

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
        """
        Retrieves the associated CloudWatch Log Group for a given Lambda function.
        If no specific log group is configured, it defaults to '/aws/lambda/{lambda_function_name}'.
        """
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
            fields @timestamp, @logStream, @message, @requestId
            | filter (@message like '{self.MESSAGE_PART_START}'
                   or @message like '{self.MESSAGE_PART_ERROR}'
                   or @message like '{self.MESSAGE_PART_END}'
                   or @message like '{self.MESSAGE_PART_REPORT}')
                  and @message not like 'INIT_START'
            | sort @timestamp
        """

        try:
            # add 1ms to query start time to make since_time non-inclusive
            query_start_time = int(
                datetime_to_epoch_milliseconds(since_time + timedelta(milliseconds=1))
            )
            query_end_time = int(datetime_to_epoch_milliseconds(datetime.now()))

            lambda_logs = cloudwatch_manager.query_logs(
                log_group_name=self.get_log_group(function_name),
                query_string=query_string,
                start_time=query_start_time,
                end_time=query_end_time,
            )

            log_processor = LambdaLogProcessor(function_name)
            for log_entry_data in lambda_logs:
                log_processor.process_log_entry(log_entry_data)
            return log_processor.generate_results()

        except Exception as e:
            error_message = f"Error getting lambda function log data: {e}"
            raise LambdaManagerException(error_message)


class LambdaLogProcessor:
    def __init__(self, function_name):
        self.function_name = function_name
        self.results: Dict[tuple, LogEntry] = {}
        self.active_requests: Dict[str, str] = {}

    def _extract_field(
        self, log_entry: List[Dict[str, str]], field_name: str
    ) -> Optional[str]:
        return next(
            (item["value"] for item in log_entry if item["field"] == field_name), None
        )

    def process_log_entry(self, log_entry: List[Dict[str, str]]):
        log_timestamp = str_utc_datetime_to_datetime(
            self._extract_field(log_entry, "@timestamp")
        )
        log_stream = self._extract_field(log_entry, "@logStream")
        request_id = self._extract_field(log_entry, "@requestId")
        message = self._extract_field(log_entry, "@message")

        if not log_stream or not message:
            return

        # handle some ERROR entries which not assigned with Request ID
        if not request_id and LambdaManager.MESSAGE_PART_ERROR in message:
            request_id = self.active_requests.get(log_stream)

        key = (log_stream, request_id)

        # handle START entry
        if LambdaManager.MESSAGE_PART_START in message:
            log_entry_obj = LogEntry(
                LambdaName=self.function_name,
                LogStream=log_stream,
                RequestId=request_id,
                Status=LambdaManager.LAMBDA_RUNNING_STATE,
                StartedOn=log_timestamp,
            )
            self.active_requests[log_stream] = request_id
            self.results[key] = log_entry_obj

        # handle ERROR entry
        elif LambdaManager.MESSAGE_PART_ERROR in message:
            if key in self.results:
                log_entry_obj = self.results[key]
                log_entry_obj.Status = LambdaManager.LAMBDA_FAILURE_STATE
                log_entry_obj.Errors.append(message)

        # handle END entry
        elif LambdaManager.MESSAGE_PART_END in message:
            if key in self.results:
                log_entry_obj = self.results[key]
                if log_entry_obj.Status != LambdaManager.LAMBDA_FAILURE_STATE:
                    log_entry_obj.Status = LambdaManager.LAMBDA_SUCCESS_STATE
                log_entry_obj.CompletedOn = log_timestamp

        # handle REPORT entry
        elif LambdaManager.MESSAGE_PART_REPORT in message:
            if key in self.results:
                log_entry_obj = self.results[key]
                log_entry_obj.Report = message

    def generate_results(self) -> list[LogEntry]:
        return list(self.results.values())

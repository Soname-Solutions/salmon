import boto3
from datetime import datetime

from pydantic import BaseModel
from typing import Optional, Union

from ..core.constants import SettingConfigResourceTypes

###########################################################
# Job-related pydantic classes


class JobRun(BaseModel):
    Id: str
    Attempt: int
    # TriggerName: str
    JobName: str
    StartedOn: Optional[datetime]
    LastModifiedOn: Optional[datetime]
    CompletedOn: Optional[datetime]
    JobRunState: str
    ErrorMessage: Optional[str] = None
    PredecessorRuns: list[str] = []
    AllocatedCapacity: int
    ExecutionTime: Optional[int]
    Timeout: int
    MaxCapacity: Optional[float]
    LogGroupName: str
    GlueVersion: str
    DPUSeconds: Optional[float] = 0.0

    @property
    def IsSuccess(self) -> bool:
        return self.JobRunState in GlueManager.Job_States_Success

    @property
    def IsFailure(self) -> bool:
        return self.JobRunState in GlueManager.Job_States_Failure


class JobRunsData(BaseModel):
    JobRuns: list[JobRun]
    NextToken: Optional[str] = None


###########################################################
# Workflow-related pydantic classes


class WorkflowStatistics(BaseModel):
    TotalActions: int
    TimeoutActions: int
    FailedActions: int
    StoppedActions: int
    SucceededActions: int
    RunningActions: int
    ErroredActions: int
    WaitingActions: int


class WorkflowRun(BaseModel):
    Name: str
    WorkflowRunId: str
    WorkflowRunProperties: dict
    StartedOn: datetime
    CompletedOn: Optional[datetime] = None
    Status: str
    ErrorMessage: Optional[str] = None
    Statistics: Optional[WorkflowStatistics] = None

    @property
    def IsSuccess(self) -> bool:
        return (self.Status in GlueManager.Workflow_States_Success) and (
            # Glue Workflow can have status "completed" even if some actions have failed, which is misleading
            # adding this check
            self.Statistics.TotalActions
            == self.Statistics.SucceededActions
        )

    @property
    def IsFailure(self) -> bool:
        return not (self.IsSuccess)

    @property
    def Duration(self) -> float:
        return (self.CompletedOn - self.StartedOn).total_seconds()


class WorkflowRunsData(BaseModel):
    Runs: list[WorkflowRun]
    NextToken: str
    ResponseMetadata: dict


###########################################################
# Glue manager classes


class GlueManagerException(Exception):
    """Exception raised for errors encountered while running Glue client methods."""

    pass


class GlueManager:
    Job_States_Success = ["SUCCEEDED"]
    Job_States_Failure = ["FAILED", "ERROR", "TIMEOUT", "STOPPED"]

    Workflow_States_Success = ["COMPLETED"]
    Workflow_States_Failure = ["STOPPED", "ERROR", "FAILURE"]
    # FAILURE is an artificial State introduced in Salmon, so we can override "false positive" state COMPLETED even
    # when there was a failure in underlying Glue Job

    Crawlers_States_Success = ["Succeeded"]
    Crawlers_States_Failure = ["Failed"]

    Catalog_State_Success = "SUCCESS"

    Data_Quality_Success = ["SUCCEEDED"]
    Data_Quality_Failure = ["FAILED", "TIMEOUT", "STOPPED"]
    Data_Quality_Context_Types = ["GLUE_DATA_CATALOG", "GLUE_JOB"]

    def __init__(self, glue_client=None):
        self.glue_client = boto3.client("glue") if glue_client is None else glue_client

    @classmethod
    def is_job_final_state(cls, state: str) -> bool:
        return state in cls.Job_States_Success or state in cls.Job_States_Failure

    @classmethod
    def is_workflow_final_state(cls, state: str) -> bool:
        return (
            state in cls.Workflow_States_Success or state in cls.Workflow_States_Failure
        )

    @classmethod
    def is_crawler_final_state(cls, state: str) -> bool:
        return (
            state in cls.Crawlers_States_Success or state in cls.Crawlers_States_Failure
        )

    def _get_all_job_names(self):
        try:
            response = self.glue_client.list_jobs()
            return response.get("JobNames")

        except Exception as e:
            raise GlueManagerException(f"Error getting list of glue jobs : {e}")

    def _get_all_workflow_names(self):
        try:
            response = self.glue_client.list_workflows()
            return response.get("Workflows")

        except Exception as e:
            raise GlueManagerException(f"Error getting list of glue workflows : {e}")

    def _get_all_crawler_names(self):
        try:
            response = self.glue_client.list_crawlers()
            return response.get("CrawlerNames")

        except Exception as e:
            raise GlueManagerException(f"Error getting list of glue crawlers : {e}")

    def _get_all_data_catalog_names(self):
        try:
            response = self.glue_client.get_databases()
            return [res["Name"] for res in response.get("DatabaseList")]

        except Exception as e:
            raise GlueManagerException(
                f"Error getting list of glue data catalogs : {e}"
            )

    def _get_all_data_quality_names(self):
        try:
            response = self.glue_client.list_data_quality_rulesets()
            return [res["Name"] for res in response.get("Rulesets")]

        except Exception as e:
            raise GlueManagerException(
                f"Error getting list of glue data quality rulesets: {e}"
            )

    def _get_all_workflow_errors(
        self, node: Union[dict, list], node_type: str = None
    ) -> list[str]:
        """Recursively extract error messages from the workflow node."""

        errors = []
        if isinstance(node, dict):
            node_type = node.get("Type", node_type)  # CRAWLER | JOB | TRIGGER
            for key, value in node.items():
                if key == "ErrorMessage" and value:
                    # Limit each error message if longer then 50 characters
                    error_msg = value[:50] + "..." if len(value) > 50 else value
                    errors.append(f"{node_type} Error: {error_msg}")
                else:
                    errors.extend(self._get_all_workflow_errors(value, node_type))

        elif isinstance(node, list):
            for item in node:
                errors.extend(self._get_all_workflow_errors(item, node_type))
        return errors

    def get_all_names(self, **kwargs):
        resource_type = kwargs.pop("resource_type", None)
        if (
            # default behavior is to return jobs list
            resource_type is None
            or resource_type == SettingConfigResourceTypes.GLUE_JOBS
        ):
            return self._get_all_job_names()
        elif resource_type == SettingConfigResourceTypes.GLUE_WORKFLOWS:
            return self._get_all_workflow_names()
        elif resource_type == SettingConfigResourceTypes.GLUE_CRAWLERS:
            return self._get_all_crawler_names()
        elif resource_type == SettingConfigResourceTypes.GLUE_DATA_CATALOGS:
            return self._get_all_data_catalog_names()
        elif resource_type == SettingConfigResourceTypes.GLUE_DATA_QUALITY:
            return self._get_all_data_quality_names()
        else:
            raise GlueManagerException(f"Unknown glue resource type {resource_type}")

    def get_job_runs(self, job_name: str, since_time: datetime) -> list[JobRun]:
        try:
            response = self.glue_client.get_job_runs(JobName=job_name)

            job_runs_data = JobRunsData(**response)
            outp = [x for x in job_runs_data.JobRuns if x.StartedOn > since_time]

            return outp

        except Exception as e:
            error_message = f"Error getting glue job runs : {e}"
            raise GlueManagerException(error_message)

    def get_workflow_runs(
        self, workflow_name: str, since_time: datetime
    ) -> list[WorkflowRun]:
        try:
            response = self.glue_client.get_workflow_runs(Name=workflow_name)

            workflow_runs_data = WorkflowRunsData(**response)
            outp = [x for x in workflow_runs_data.Runs if x.StartedOn > since_time]

            return outp

        except Exception as e:
            error_message = f"Error getting glue workflow runs : {e}"
            raise GlueManagerException(error_message)

    def generate_workflow_run_error_message(
        self, workflow_name: str, workflow_run_id: str
    ) -> str:
        """Generate an error message related to the particular workflow run ID"""
        try:
            workflow_run = self.glue_client.get_workflow_run(
                Name=workflow_name,
                RunId=workflow_run_id,
                IncludeGraph=True,
            )

            # Extract error messages from the workflow run graph
            graph = workflow_run.get("Run", {}).get("Graph", {})
            error_messages = self._get_all_workflow_errors(graph)

            # Join error messages into a single string and limit its length
            workflow_error_message = (
                "; ".join(error_messages) if error_messages else None
            )
            error_count = len(error_messages)
            if error_count > 1:
                message_prefix = f"Total Errors: {error_count}. "
                workflow_error_message = (
                    message_prefix + workflow_error_message[:100] + "..."
                    if len(workflow_error_message) > 100
                    else message_prefix + workflow_error_message
                )
            return workflow_error_message

        except Exception as e:
            error_message = f"Error getting glue workflow error message: {e}"
            raise GlueManagerException(error_message)

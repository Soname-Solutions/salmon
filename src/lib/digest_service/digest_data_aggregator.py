from pydantic import BaseModel
from typing import Optional, Dict, List, DefaultDict
from collections import defaultdict

from lib.core.constants import DigestSettings, SettingConfigs
from lib.event_mapper import ExecutionInfoUrlMixin


class ResourceRun(BaseModel):
    resource_name: str
    failed: int = 0
    succeeded: int = 0
    execution: int = 0
    job_run_id: Optional[str] = None
    error_message: Optional[str] = None
    execution_time_sec: Optional[float] = 0.0
    failed_attempts: int = 0
    glue_table_name: Optional[str] = None
    glue_db_name: Optional[str] = None
    glue_catalog_id: Optional[str] = None
    glue_job_name: Optional[str] = None
    context_type: Optional[str] = None
    log_stream: Optional[str] = None


class ResourceConfig(BaseModel):
    name: str
    region_name: str
    account_id: str
    minimum_number_of_runs: int = 0
    sla_seconds: int = 0


class AggregatedEntry(BaseModel):
    Executions: int = 0
    Success: int = 0
    Errors: int = 0
    Warnings: int = 0
    ErrorComments: List[str] = []
    WarningComments: List[str] = []
    MinRuns: int = 0
    SLA: int = 0
    InsufficientRuns: bool = (
        False  # Indicates if there have been less runs than expected
    )
    HasSLABreach: bool = False  # Indicates if any SLA breach occurred
    HasFailedAttempts: bool = False  # Indicates if any successfull run required retries

    @property
    def Status(self) -> str:
        if self.Errors > 0 or self.InsufficientRuns:
            return DigestSettings.STATUS_ERROR
        elif self.Warnings > 0:
            return DigestSettings.STATUS_WARNING
        return DigestSettings.STATUS_OK

    @property
    def CommentsStr(self) -> str:
        """Returns the comments as a single string separated by newlines."""
        return "<br/>".join(self.generate_comments())

    def generate_comments(self) -> list:
        """Generates a list of comments based on errors, warnings, and SLA checks."""
        comments = []

        # Error comments first
        if self.ErrorComments:
            comments.append("Some runs have failed:")
            comments.extend(set(self.ErrorComments))

        # Comment on insufficient runs
        if self.InsufficientRuns:
            comments.append(
                f"Insufficient runs: {self.Executions} run(s) during the monitoring period "
                f"(at least {self.MinRuns} expected)."
            )

        # Warning comment about retries
        if self.HasFailedAttempts and self.WarningComments:
            comments.append(
                "Some runs have succeeded after one or more retry attempts:"
            )
            comments.extend(set(self.WarningComments))

        # Warning comment about SLA
        if self.HasSLABreach:
            comments.append(f"Some runs haven't met SLA (={self.SLA} sec).")

        return comments


class SummaryEntry(BaseModel):
    ResourceType: str
    MonitoringGroup: str
    EntryList: list[AggregatedEntry]

    @property
    def TotalExecutions(self) -> int:
        return sum(entry.Executions for entry in self.EntryList)

    @property
    def TotalSuccess(self) -> int:
        return sum(entry.Success for entry in self.EntryList)

    @property
    def TotalFailures(self) -> int:
        return sum(
            (entry.Errors + int(entry.InsufficientRuns)) for entry in self.EntryList
        )

    @property
    def TotalWarnings(self) -> int:
        return sum(entry.Warnings for entry in self.EntryList)

    @property
    def Status(self) -> str:
        if self.TotalFailures > 0:
            return DigestSettings.STATUS_ERROR
        elif self.TotalWarnings > 0:
            return DigestSettings.STATUS_WARNING
        return DigestSettings.STATUS_OK

    @property
    def ServiceName(self) -> str:
        return SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES.get(self.ResourceType)


class DigestDataAggregator:
    """
    Base Class which provides unified functionality for aggregating metrics in the digest report.
    """

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.aggregated_runs: DefaultDict[str, AggregatedEntry] = defaultdict(
            AggregatedEntry
        )

    def _get_runs_by_resource_name(
        self, data: dict, resource_name: str
    ) -> list[ResourceRun]:
        """Gets runs related to specific resource name."""
        return [
            ResourceRun(**entry)
            for entries in data.values()
            for entry in entries
            if entry["resource_name"] == resource_name
        ]

    def _check_sla_breach(
        self, agg_entry: AggregatedEntry, resource_run: ResourceRun
    ) -> None:
        """Checks if the run has breached SLA."""
        if agg_entry.SLA > 0 and resource_run.execution_time_sec > agg_entry.SLA:
            agg_entry.Warnings += 1
            agg_entry.HasSLABreach = True

    def _check_succeeded_with_retry(
        self, agg_entry: AggregatedEntry, resource_run: ResourceRun
    ) -> None:
        """Checks if the run succeeded after retries."""
        if resource_run.succeeded > 0 and resource_run.failed_attempts > 0:
            agg_entry.Warnings += 1
            agg_entry.HasFailedAttempts = True

    def _check_insufficient_runs(self, agg_entry: AggregatedEntry) -> None:
        """Checks if the requirement on the min number of runs is not met."""
        if agg_entry.MinRuns > 0 and agg_entry.Executions < agg_entry.MinRuns:
            agg_entry.InsufficientRuns = True

    def _generate_job_run_url(
        self, resource_run: ResourceRun, resource_config: ResourceConfig
    ) -> str:
        """Generates the URL for a specific job run based on resource run details."""
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=resource_config.region_name,
            resource_name=resource_run.resource_name,
            account_id=resource_config.account_id,
            run_id=resource_run.job_run_id,
            glue_table_name=resource_run.glue_table_name,
            glue_db_name=resource_run.glue_db_name,
            glue_catalog_id=resource_run.glue_catalog_id,
            glue_job_name=resource_run.glue_job_name,
            context_type=resource_run.context_type,
            log_stream=resource_run.log_stream,
        )

    def _append_error_comments(
        self,
        resource_run: ResourceRun,
        resource_config: ResourceConfig,
        agg_entry: AggregatedEntry,
    ) -> None:
        """Adds error/warning comments based on failed runs/attempts."""
        is_failed = resource_run.failed > 0
        is_successful_with_retries = (
            resource_run.succeeded > 0 and resource_run.failed_attempts > 0
        )

        if is_failed or is_successful_with_retries:
            job_run_url = self._generate_job_run_url(resource_run, resource_config)

            max_msg_length = DigestSettings.MAX_ERROR_MESSAGE_LENGTH
            truncated_error_message = (
                resource_run.error_message[:max_msg_length] + "..."
                if len(resource_run.error_message) > max_msg_length
                else resource_run.error_message
            )
            error_comment = (
                f" - <a href='{job_run_url}'> ERROR: {truncated_error_message}</a>"
            )

            # Append error or warning comments to the appropriate list
            if is_failed:
                agg_entry.ErrorComments.append(error_comment)
            if is_successful_with_retries:
                agg_entry.WarningComments.append(error_comment)

    def _process_single_run(
        self,
        agg_entry: AggregatedEntry,
        resource_run: ResourceRun,
        resource_config: ResourceConfig,
    ) -> None:
        """Aggregates runs related to a specific resource name."""
        agg_entry.Errors += resource_run.failed
        agg_entry.Success += resource_run.succeeded
        agg_entry.Executions += resource_run.execution

        self._append_error_comments(resource_run, resource_config, agg_entry)
        self._check_sla_breach(agg_entry, resource_run)
        self._check_succeeded_with_retry(agg_entry, resource_run)

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: List[dict]
    ) -> Dict[str, AggregatedEntry]:
        """Aggregates data for each resource specified in the configurations."""

        # convert list of dictionaries to list of ResourceConfig instances
        configs = [ResourceConfig(**item) for item in resources_config]
        for resource_config in configs:
            runs = self._get_runs_by_resource_name(extracted_runs, resource_config.name)
            agg_entry = self.aggregated_runs[resource_config.name]
            agg_entry.MinRuns = resource_config.minimum_number_of_runs
            agg_entry.SLA = resource_config.sla_seconds

            for run in runs:
                self._process_single_run(agg_entry, run, resource_config)

            self._check_insufficient_runs(agg_entry)

        return dict(self.aggregated_runs)

    def get_summary_entry(
        self, group_name: str, aggregated_runs: Dict[str, AggregatedEntry]
    ) -> SummaryEntry:
        """Calculates and returns summary entry for aggregated_runs."""

        return SummaryEntry(
            ResourceType=self.resource_type,
            MonitoringGroup=group_name,
            EntryList=list(aggregated_runs.values()),
        )

from pydantic import BaseModel
from typing import Dict, List, DefaultDict
from collections import defaultdict

from lib.core.constants import DigestSettings
from lib.event_mapper import ExecutionInfoUrlMixin


class AggregatedEntry(BaseModel):
    Executions: int = 0
    Failures: int = 0
    Success: int = 0
    Errors: int = 0
    Warnings: int = 0
    Comments: List[str] = []
    HasSLABreach: bool = False  # Indicates if any SLA breaches occurred
    HasFailedAttempts: bool = False  # Indicates if any runs required retries

    @property
    def Status(self) -> str:
        if self.Errors > 0 or self.Failures > 0:
            return DigestSettings.STATUS_ERROR
        elif self.Warnings > 0:
            return DigestSettings.STATUS_WARNING
        return DigestSettings.STATUS_OK


class SummaryEntry(BaseModel):
    Executions: int = 0
    Success: int = 0
    Failures: int = 0
    Warnings: int = 0

    @property
    def Status(self) -> str:
        if self.Failures > 0:
            return DigestSettings.STATUS_ERROR
        elif self.Warnings > 0:
            return DigestSettings.STATUS_WARNING
        return DigestSettings.STATUS_OK


class DigestDataAggregator:
    def __init__(self):
        self.aggregated_runs: DefaultDict[str, AggregatedEntry] = defaultdict(
            AggregatedEntry
        )
        self.summary_entry = SummaryEntry()

    def _get_runs_by_resource_name(self, data: dict, resource_name: str) -> list:
        """Gets runs related to specific resource name."""
        return [
            entry
            for entries in data.values()
            for entry in entries
            if entry["resource_name"] == resource_name
        ]

    def _finalize_comments(
        self, resource_agg_entry: AggregatedEntry, resource_config: dict
    ) -> None:
        # remove duplicate comments
        resource_agg_entry.Comments = list(set(resource_agg_entry.Comments))

        # add warnings
        if resource_agg_entry.HasSLABreach:
            resource_agg_entry.Comments.append(
                f"WARNING: Some runs haven't met SLA (={resource_config.get('sla_seconds', 0)} sec)."
            )
        if resource_agg_entry.HasFailedAttempts:
            resource_agg_entry.Comments.append(
                "WARNING: Some runs have succeeded after one or more retry attempts."
            )

        # add a general failure comment
        if resource_agg_entry.Errors > 0:
            resource_agg_entry.Comments.insert(0, "Some runs have failed")

        # check if the requirement on min number of runs was met
        min_runs = resource_config.get("minimum_number_of_runs", 0)
        if min_runs > 0 and resource_agg_entry.Executions < min_runs:
            resource_agg_entry.Failures += 1
            resource_agg_entry.Comments.append(
                f"{resource_agg_entry.Executions} runs during the monitoring period (at least {min_runs} expected)"
            )

    def _append_error_comments(
        self,
        resource_run: dict,
        resource_type: str,
        resource_config: dict,
        resource_agg_entry: AggregatedEntry,
    ) -> None:
        """Adds error comments based on failed runs."""

        if int(resource_run["failed"]) > 0:
            job_run_url = ExecutionInfoUrlMixin.get_url(
                resource_type=resource_type,
                region_name=resource_config["region_name"],
                resource_name=resource_run["resource_name"],
                account_id=resource_config["account_id"],
                run_id=resource_run["job_run_id"],
                glue_table_name=resource_run.get("glue_table_name"),
                glue_db_name=resource_run.get("glue_db_name"),
                glue_catalog_id=resource_run.get("glue_catalog_id"),
                glue_job_name=resource_run.get("glue_job_name"),
                context_type=resource_run.get("context_type"),
            )

            error_message = resource_run.get("error_message", "Unknown errors")
            if job_run_url:
                if len(error_message) > DigestSettings.MAX_ERROR_MESSAGE_LENGTH:
                    error_message = (
                        error_message[: DigestSettings.MAX_ERROR_MESSAGE_LENGTH] + "..."
                    )
                error_comment = f" - <a href='{job_run_url}'>ERROR: {error_message}</a>"
            else:
                error_comment = f" - {error_message}"

            resource_agg_entry.Comments.append(error_comment)

    def _process_single_run(
        self,
        resource_type: str,
        resource_agg_entry: AggregatedEntry,
        resource_run: dict,
        resource_config: dict,
    ) -> None:
        """Aggregates runs related to a specific resource name."""
        resource_agg_entry.Errors += int(resource_run["failed"])
        resource_agg_entry.Success += int(resource_run["succeeded"])
        resource_agg_entry.Executions += int(resource_run["execution"])

        # for each failed run, the error details will be added in the comment section
        self._append_error_comments(
            resource_run=resource_run,
            resource_type=resource_type,
            resource_config=resource_config,
            resource_agg_entry=resource_agg_entry,
        )

        # check for SLA breach
        sla_seconds = resource_config.get("sla_seconds", 0)
        execution_time_sec = float(resource_run.get("execution_time_sec", 0))
        if sla_seconds > 0 and execution_time_sec > sla_seconds:
            resource_agg_entry.Warnings += 1
            resource_agg_entry.HasSLABreach = True

        # check for failed attempts before succeeding (relevant for Lambda Functions)
        succeeded_runs = int(resource_run.get("succeeded", 0))
        failed_attempts = int(resource_run.get("failed_attempts", 0))
        if succeeded_runs > 0 and failed_attempts > 0:
            resource_agg_entry.Warnings += 1
            resource_agg_entry.HasFailedAttempts = True

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: list, resource_type: str
    ) -> Dict[str, AggregatedEntry]:
        """Aggregates data for each resource specified in the configurations."""
        for resource_config in resources_config:
            resource_name = resource_config["name"]
            resource_runs = self._get_runs_by_resource_name(
                data=extracted_runs, resource_name=resource_name
            )
            resource_agg_entry = self.aggregated_runs[resource_name]

            for resource_run in resource_runs:
                self._process_single_run(
                    resource_type=resource_type,
                    resource_agg_entry=resource_agg_entry,
                    resource_run=resource_run,
                    resource_config=resource_config,
                )

            self._finalize_comments(
                resource_agg_entry=resource_agg_entry,
                resource_config=resource_config,
            )

        return dict(self.aggregated_runs)

    def get_summary_entry(
        self, aggregated_runs: Dict[str, AggregatedEntry]
    ) -> SummaryEntry:
        """Calculates and returns summary entry for aggregated_runs."""

        for entry in aggregated_runs.values():
            self.summary_entry.Executions += entry.Executions
            self.summary_entry.Success += entry.Success
            self.summary_entry.Failures += entry.Errors + entry.Failures
            self.summary_entry.Warnings += entry.Warnings

        return self.summary_entry

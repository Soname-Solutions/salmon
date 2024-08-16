from collections import defaultdict
from lib.core.constants import DigestSettings
from lib.event_mapper import ExecutionInfoUrlMixin


class DigestDataAggregator:
    def __init__(self):
        self.aggregated_runs = defaultdict(
            lambda: {
                "Status": DigestSettings.STATUS_OK,
                "Executions": 0,
                "Failures": 0,
                "values": {
                    "Success": 0,
                    "Errors": 0,
                    "Warnings": 0,
                    "Comments": [],
                },
            }
        )
        self.summary_entry = {
            "Status": DigestSettings.STATUS_OK,
            "Executions": 0,
            "Success": 0,
            "Failures": 0,
            "Warnings": 0,
        }

    def _get_runs_by_resource_name(self, data: dict, resource_name: str) -> list:
        """Gets runs related to specific resource name."""
        return [
            entry
            for entries in data.values()
            for entry in entries
            if entry["resource_name"] == resource_name
        ]

    def _assign_row_status(
        self, aggregated_runs: dict, resource_name: str, resource_config: dict
    ):
        """Assigns row status based on warnings, errors."""

        values = aggregated_runs[resource_name]["values"]
        # to remove duplicated comments
        values["Comments"] = list(set(values["Comments"]))
        warnings_count = values["Warnings"]
        errors_count = values["Errors"]
        min_runs = resource_config["minimum_number_of_runs"]
        executions = aggregated_runs[resource_name]["Executions"]

        # Warning status if some runs haven't met SLA
        if warnings_count > 0:
            aggregated_runs[resource_name]["Status"] = DigestSettings.STATUS_WARNING
            values["Comments"].append(
                f"Some runs haven't met SLA (={resource_config['sla_seconds']} sec)"
            )

        # Error status if some runs have failed or there have been fewer runs than expected
        if errors_count > 0 or (min_runs > 0 and executions < min_runs):
            aggregated_runs[resource_name]["Status"] = DigestSettings.STATUS_ERROR

            if errors_count > 0:
                values["Comments"].insert(0, "Some runs have failed")

            if min_runs > 0 and executions < min_runs:
                aggregated_runs[resource_name]["Failures"] += 1
                values["Comments"].append(
                    f"{executions} runs during the monitoring period (at least {min_runs} expected)"
                )

        # to start each comment from the new line in the digest message
        values["Comments"] = "<br/>".join(values["Comments"])

    def _get_error_comments(
        self,
        resource_run: dict,
        resource_type: str,
        resource_config: dict,
        resource_values: dict,
    ) -> list:
        if int(resource_run["failed"]) > 0:
            job_run_url = ExecutionInfoUrlMixin.get_url(
                resource_type=resource_type,
                region_name=resource_config["region_name"],
                resource_name=resource_run["resource_name"],
                account_id=resource_config["account_id"],
                run_id=resource_run["job_run_id"],
                # extra arguments required for Glue DQ execution link
                glue_table_name=resource_run.get("glue_table_name"),
                glue_db_name=resource_run.get("glue_db_name"),
                glue_catalog_id=resource_run.get("glue_catalog_id"),
                glue_job_name=resource_run.get("glue_job_name"),
                context_type=resource_run.get("context_type"),
            )

            # construct error comment based on the job run URL and error message
            error_message = resource_run.get("error_message", "Unknown errors")
            if job_run_url:
                # truncate error message if > 100 chars
                truncated_message = (
                    (error_message[:100] + "...")
                    if len(error_message) > 100
                    else error_message
                )
                error_comment = (
                    f" - <a href='{job_run_url}'>ERROR: {truncated_message}</a>"
                )
            else:
                # Use error message directly if no job run URL (defaults to 'Unknown errors')
                error_comment = f" - {error_message}"

            resource_values["Comments"].append(error_comment)

    def _process_single_run(
        self,
        resource_type: str,
        resource_name: str,
        resource_run: dict,
        resource_config: dict,
        aggregated_runs: dict,
    ):
        """Aggregates runs related to specific resource name."""
        resource_values = aggregated_runs[resource_name]["values"]
        resource_values["Errors"] += int(resource_run["failed"])
        resource_values["Success"] += int(resource_run["succeeded"])
        aggregated_runs[resource_name]["Executions"] += int(resource_run["execution"])

        # for each failed run, the error details will be added in the comment section
        self._get_error_comments(
            resource_run=resource_run,
            resource_type=resource_type,
            resource_config=resource_config,
            resource_values=resource_values,
        )

        # add a warning if the run hasn't met SLA
        sla_seconds = resource_config["sla_seconds"]
        execution_time_sec = resource_run["execution_time_sec"]
        if (
            execution_time_sec is not None
            and sla_seconds != 0
            and float(execution_time_sec) > sla_seconds
        ):
            resource_values["Warnings"] += 1

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: list, resource_type: str
    ) -> dict:
        # iterate over each resource name specified in the config
        for resource_config in resources_config:
            resource_name = resource_config["name"]
            resource_runs = self._get_runs_by_resource_name(
                data=extracted_runs, resource_name=resource_name
            )

            for resource_run in resource_runs:
                self._process_single_run(
                    resource_type=resource_type,
                    resource_name=resource_name,
                    resource_run=resource_run,
                    resource_config=resource_config,
                    aggregated_runs=self.aggregated_runs,
                )

            self._assign_row_status(
                aggregated_runs=self.aggregated_runs,
                resource_name=resource_name,
                resource_config=resource_config,
            )

        return dict(self.aggregated_runs)

    def get_summary_entry(self, data: dict) -> dict:
        """Calculates summary entry for each resource type and monitoring group."""

        for resource_data in data.values():
            self.summary_entry["Executions"] += resource_data["Executions"]
            self.summary_entry["Success"] += resource_data["values"]["Success"]
            self.summary_entry["Failures"] += (
                resource_data["values"]["Errors"] + resource_data["Failures"]
            )
            self.summary_entry["Warnings"] += resource_data["values"]["Warnings"]

        # assign summary status
        if self.summary_entry["Failures"] > 0:
            self.summary_entry["Status"] = DigestSettings.STATUS_ERROR
        elif self.summary_entry["Warnings"] > 0:
            self.summary_entry["Status"] = DigestSettings.STATUS_WARNING

        return self.summary_entry

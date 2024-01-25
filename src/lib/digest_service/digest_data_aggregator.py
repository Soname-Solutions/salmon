from collections import defaultdict
from lib.core.constants import DigestSettings
from lib.metrics_extractor import get_job_run_url


class DigestDataAggregator:
    def _get_runs_by_resource_name(self, data: dict, resource_name: str) -> list:
        """Gets runs related to specific resource name."""
        return [
            entry
            for entries in data.values()
            for entry in entries
            if entry["resource_name"] == resource_name
        ]

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

        # for each failed run, the error link will be added in the comment section
        if resource_run["failed"] != 0 and resource_run["job_run_id"]:
            job_run_url = get_job_run_url(
                resource_type=resource_type,
                region_name=resource_config["region_name"],
                account_id=resource_config["account_id"],
                resource_name=resource_run["resource_name"],
                run_id=resource_run["job_run_id"],
            )
            error_link = (
                f" - <a href={job_run_url}>{resource_run['error_message'][:50]}</a>"
            )
            resource_values["Comments"].append(error_link)

        # add a warning if the run hasn't met SLA
        sla_seconds = resource_config["sla_seconds"]
        execution_time_sec = float(resource_run["execution_time_sec"])
        if sla_seconds != 0 and execution_time_sec > sla_seconds:
            resource_values["Warnings"] += 1

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: list, resource_type: str
    ) -> dict:
        """Aggregates runs for each resource type and monitoring group."""
        aggregated_runs = defaultdict(
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
                    aggregated_runs=aggregated_runs,
                )

            # assign row status
            # Warning status if some runs haven't met SLA
            warnings_count = aggregated_runs[resource_name]["values"]["Warnings"]
            if warnings_count > 0:
                aggregated_runs[resource_name]["Status"] = DigestSettings.STATUS_WARNING
                aggregated_runs[resource_name]["values"]["Comments"].append(
                    f"Some runs haven't met SLA (={resource_config['sla_seconds']} sec)"
                )

            # Error status if some runs have failed or there have been fewer runs than expected
            errors_count = aggregated_runs[resource_name]["values"]["Errors"]
            min_runs = resource_config["minimum_number_of_runs"]
            executions = aggregated_runs[resource_name]["Executions"]

            if errors_count > 0 or (min_runs > 0 and executions < min_runs):
                aggregated_runs[resource_name]["Status"] = DigestSettings.STATUS_ERROR

                if errors_count > 0:
                    aggregated_runs[resource_name]["values"]["Comments"].insert(
                        0, "Some runs have failed"
                    )

                if min_runs > 0 and executions < min_runs:
                    aggregated_runs[resource_name]["Failures"] += 1
                    aggregated_runs[resource_name]["values"]["Comments"].append(
                        f"{executions} runs during the monitoring period (at least {min_runs} expected)"
                    )

            # to start each comment from the new line in the digest message
            aggregated_runs[resource_name]["values"]["Comments"] = "<br/>".join(
                aggregated_runs[resource_name]["values"]["Comments"]
            )

        return dict(aggregated_runs)

    def get_summary_entry(self, data: dict) -> dict:
        """Calculates summary entry for each resource type and monitoring group."""
        summary_entry = {
            "Status": DigestSettings.STATUS_OK,
            "Executions": 0,
            "Success": 0,
            "Failures": 0,
            "Warnings": 0,
        }

        for resource_data in data.values():
            summary_entry["Executions"] += resource_data["Executions"]
            summary_entry["Success"] += resource_data["values"]["Success"]
            summary_entry["Failures"] += (
                resource_data["values"]["Errors"] + resource_data["Failures"]
            )
            summary_entry["Warnings"] += resource_data["values"]["Warnings"]

        # assign summary status
        if summary_entry["Failures"] > 0:
            summary_entry["Status"] = DigestSettings.STATUS_ERROR
        elif summary_entry["Warnings"] > 0:
            summary_entry["Status"] = DigestSettings.STATUS_WARNING

        return summary_entry

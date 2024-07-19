from datetime import datetime
from typing import Tuple

from lib.aws.glue_manager import GlueManager, RulesetRun
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
from lib.core import datetime_utils


class GlueDataQualityMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue data quality metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[RulesetRun]:
        glue_man = GlueManager(self.get_aws_service_client())
        result_ids = glue_man.list_data_quality_results(
            since_time=since_time,
        )

        if result_ids:
            ruleset_runs = glue_man.get_data_quality_runs(
                resource_name=self.resource_name, result_ids=result_ids
            )
            return ruleset_runs
        return []

    def _data_to_timestream_records(self, ruleset_runs: list[RulesetRun]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for ruleset_run in ruleset_runs:
            dimensions = [{"Name": "dq_result_id", "Value": ruleset_run.ResultId}]
            common_metric_values = [
                ("score", ruleset_run.Score, "DOUBLE"),
                ("context_type", ruleset_run.ContextType, "VARCHAR"),
                ("execution", 1, "BIGINT"),
                ("succeeded", int(ruleset_run.IsSuccess), "BIGINT"),
                ("failed", int(ruleset_run.IsFailure), "BIGINT"),
                ("rules_succeeded", ruleset_run.numRulesSucceeded, "BIGINT"),
                ("rules_failed", ruleset_run.numRulesFailed, "BIGINT"),
                ("total_rules", ruleset_run.totalRules, "BIGINT"),
                ("execution_time_sec", ruleset_run.Duration, "DOUBLE"),
                ("error_message", ruleset_run.ErrorString, "VARCHAR"),
            ]

            if ruleset_run.DataSource and ruleset_run.DataSource.GlueTable:
                specific_metrics = [
                    ("ruleset_run_id", ruleset_run.RulesetEvaluationRunId, "VARCHAR"),
                    (
                        "glue_table_name",
                        ruleset_run.DataSource.GlueTable.TableName,
                        "VARCHAR",
                    ),
                    (
                        "glue_db_name",
                        ruleset_run.DataSource.GlueTable.DatabaseName,
                        "VARCHAR",
                    ),
                    ("glue_job_name", None, "VARCHAR"),
                    ("glue_job_run_id", None, "VARCHAR"),
                ]

            else:
                specific_metrics = [
                    ("ruleset_run_id", None, "VARCHAR"),
                    ("glue_table_name", None, "VARCHAR"),
                    ("glue_db_name", None, "VARCHAR"),
                    ("glue_job_name", ruleset_run.JobName, "VARCHAR"),
                    ("glue_job_run_id", ruleset_run.JobRunId, "VARCHAR"),
                ]
            metric_values = common_metric_values + specific_metrics

            measure_values = [
                {
                    "Name": metric_name,
                    "Value": str(metric_value),
                    "Type": metric_type,
                }
                for metric_name, metric_value, metric_type in metric_values
            ]

            record_time = datetime_utils.datetime_to_epoch_milliseconds(
                ruleset_run.StartedOn
            )

            records.append(
                {
                    "Dimensions": dimensions,
                    "MeasureName": self.EXECUTION_MEASURE_NAME,
                    "MeasureValueType": "MULTI",
                    "MeasureValues": measure_values,
                    "Time": record_time,
                }
            )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> Tuple[list, dict]:
        ruleset_runs = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(ruleset_runs)
        return records, common_attributes

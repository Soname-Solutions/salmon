from datetime import datetime, timezone
from typing import Optional
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

from pydantic import BaseModel

from lib.aws.glue_manager import GlueManager, Crawl


class GlueCrawlersMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue crawlers metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[Crawl]:
        since_epoch_milliseconds = int(since_time.timestamp() * 1000)
        glue_man = GlueManager(super().get_aws_service_client())
        return glue_man.get_crawls(
            crawler_name=self.resource_name,
            since_epoch_milliseconds=since_epoch_milliseconds,
        )

    def _data_to_timestream_records(self, crawls_data: list[Crawl]) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        records = []
        common_attributes = {"Dimensions": common_dimensions}

        records = []
        for crawl in crawls_data:
            # include only completed Crawls
            if crawl.IsCompleted:
                dimensions = [{"Name": "crawl_id", "Value": crawl.CrawlId}]

                dpu_seconds = round(crawl.DPUHour * 60 * 60, 3)

                metric_values = [
                    ("execution", 1, "BIGINT"),
                    ("succeeded", int(crawl.IsSuccess), "BIGINT"),
                    ("failed", int(crawl.IsFailure), "BIGINT"),
                    ("duration_sec", crawl.Duration, "DOUBLE"),
                    ("dpu_seconds", dpu_seconds, "DOUBLE"),
                    ("error_message", crawl.ErrorMessage, "VARCHAR"),
                    ("tables_added", crawl.SummaryParsed.TablesAdded, "BIGINT"),
                    ("tables_updated", crawl.SummaryParsed.TablesUpdated, "BIGINT"),
                    ("tables_deleted", crawl.SummaryParsed.TablesDeleted, "BIGINT"),
                    ("partitions_added", crawl.SummaryParsed.PartitionsAdded, "BIGINT"),
                    (
                        "partitions_updated",
                        crawl.SummaryParsed.PartitionsUpdated,
                        "BIGINT",
                    ),
                    (
                        "partitions_deleted",
                        crawl.SummaryParsed.PartitionsDeleted,
                        "BIGINT",
                    ),
                ]
                measure_values = [
                    {
                        "Name": metric_name,
                        "Value": str(metric_value),
                        "Type": metric_type,
                    }
                    for metric_name, metric_value, metric_type in metric_values
                ]

                record_time = str(crawl.StartTimeEpochMilliseconds)

                records.append(
                    {
                        "Dimensions": dimensions,
                        "MeasureName": self.EXECUTION_MEASURE_NAME,
                        "MeasureValueType": "MULTI",
                        "MeasureValues": measure_values,
                        "Time": record_time,
                        "TimeUnit": "MILLISECONDS",
                    }
                )

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        crawls_data = self._extract_metrics_data(since_time=since_time)
        records, common_attributes = self._data_to_timestream_records(crawls_data)
        return records, common_attributes

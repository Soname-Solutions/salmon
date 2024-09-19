from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

from lib.aws.glue_manager import GlueManager, CrawlerData, CrawlerMetricsList

from pydantic import BaseModel


class GlueCrawlersMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue crawlers metrics
    """

    def _extract_metrics_data(
        self, since_time: datetime
    ) -> tuple[CrawlerData, CrawlerMetricsList]:
        glue_man = GlueManager(super().get_aws_service_client())
        crawler_data = glue_man.get_crawler_data(crawler_name=self.resource_name)
        crawler_metrics = glue_man.get_crawler_metrics(crawler_name=self.resource_name)

        return crawler_data, crawler_metrics

    def _data_to_timestream_records(
        self, crawler_data: CrawlerData, crawler_metrics: CrawlerMetricsList
    ) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}

        records = []
        if GlueManager.is_crawl_final_state(
            crawler_data.State
        ):  # checking if crawler run is completed
            if not (crawler_data.LastCrawl):
                raise (
                    "LastCrawl data is unavailable. It should be at this stage, can't proceed."
                )

            # we don't have run_id for crawler, so can't add this as a dim value - only the last execution
            dimensions = []

            metric_values = [
                ("execution", 1, "BIGINT"),
                ("succeeded", int(crawler_data.LastCrawl.IsSuccess), "BIGINT"),
                ("failed", int(crawler_data.LastCrawl.IsFailure), "BIGINT"),
                ("error_message", crawler_data.LastCrawl.ErrorMessage, "VARCHAR"),
                ("tables_created", crawler_metrics.TablesCreated, "BIGINT"),
                ("tables_updated", crawler_metrics.TablesUpdated, "BIGINT"),
                ("tables_deleted", crawler_metrics.TablesDeleted, "BIGINT"),
            ]

            measure_values = [
                {
                    "Name": metric_name,
                    "Value": str(metric_value),
                    "Type": metric_type,
                }
                for metric_name, metric_value, metric_type in metric_values
            ]

            record_time = str(crawler_data.LastCrawl.StartTimeEpochMilliseconds)

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

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        crawler_data, crawler_metrics = self._extract_metrics_data(
            since_time=since_time
        )
        records, common_attributes = self._data_to_timestream_records(
            crawler_data, crawler_metrics
        )
        return records, common_attributes

from datetime import datetime, timezone
from typing import Optional
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
import boto3

from pydantic import BaseModel

from lib.aws.glue_manager import GlueManager, CrawlerData, CrawlerMetricsList
from lib.aws.timestream_manager import (
    TimeStreamQueryRunner,
    convert_timestream_datetime_str,
)


class CrawlerLatestRecord(BaseModel):
    start_time_utc: Optional[datetime] = datetime(1970, 1, 1).replace(tzinfo=timezone.utc)
    tables_created_total: Optional[int] = 0
    tables_updated_total: Optional[int] = 0
    tables_deleted_total: Optional[int] = 0


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

    def _get_latest_timestream_record(self):
        client = boto3.client("timestream-query")
        runner = TimeStreamQueryRunner(client)

        is_table_empty = runner.is_table_empty(
            self.timestream_db_name, self.timestream_metrics_table_name
        )
        if is_table_empty:
            return CrawlerLatestRecord()

        query = f"""SELECT time, tables_created_total, tables_updated_total, tables_deleted_total
                    FROM (SELECT resource_name, time, tables_created_total, tables_updated_total, tables_deleted_total
                                , max(time) over (partition by resource_name) as max_time
                            FROM "{self.timestream_db_name}"."{self.timestream_metrics_table_name}" 
                            WHERE resource_name = '{self.resource_name}'
                        )
                    WHERE time = max_time
        """
        result = runner.execute_query(query)

        if not (result):
            return CrawlerLatestRecord()

        record = result[0]
        return CrawlerLatestRecord(
            start_time_utc=convert_timestream_datetime_str(record["time"]),
            tables_created_total=record["tables_created_total"],
            tables_updated_total=record["tables_updated_total"],
            tables_deleted_total=record["tables_deleted_total"],
        )

    def _data_to_timestream_records(
        self, crawler_data: CrawlerData, crawler_metrics: CrawlerMetricsList
    ) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        records = []
        common_attributes = {"Dimensions": common_dimensions}
        
        # checking if 
        # 1. crawler run is not currently running       
        # 2. there was at least one crawl completed
        # if not -> return empty data
        if not(GlueManager.is_crawl_final_state(crawler_data.State)) or \
           not (crawler_data.LastCrawl):
              return [], {}
        
        previous_record: CrawlerLatestRecord = self._get_latest_timestream_record()

        # if it's still the same record = skip adding metrics
        if crawler_data.LastCrawl.StartTime <= previous_record.start_time_utc:
            print('No newer record for Glue Crawler execution found')
            return [], {}
        
        tables_created_delta = crawler_metrics.TablesCreated - previous_record.tables_created_total
        tables_updated_delta = crawler_metrics.TablesUpdated - previous_record.tables_updated_total
        tables_deleted_total = crawler_metrics.TablesDeleted - previous_record.tables_deleted_total

        # we don't have run_id for crawler, so can't add this as a dim value - only the last execution
        dimensions = []

        metric_values = [
            ("execution", 1, "BIGINT"),
            ("succeeded", int(crawler_data.LastCrawl.IsSuccess), "BIGINT"),
            ("failed", int(crawler_data.LastCrawl.IsFailure), "BIGINT"),
            ("error_message", crawler_data.LastCrawl.ErrorMessage, "VARCHAR"),
            ("tables_created_total", crawler_metrics.TablesCreated, "BIGINT"),
            ("tables_updated_total", crawler_metrics.TablesUpdated, "BIGINT"),
            ("tables_deleted_total", crawler_metrics.TablesDeleted, "BIGINT"),
            ("tables_created_delta", tables_created_delta, "BIGINT"),  
            ("tables_updated_delta", tables_updated_delta, "BIGINT"),
            ("tables_deleted_delta", tables_deleted_total, "BIGINT"),
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
                "TimeUnit": "MILLISECONDS",
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

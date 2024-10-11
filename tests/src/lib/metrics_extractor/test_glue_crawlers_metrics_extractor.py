from datetime import datetime

from unittest.mock import patch
import pytest

from lib.metrics_extractor import GlueCrawlersMetricExtractor
from lib.aws.glue_manager import Crawl, CrawlSummary

from common import boto3_client_creator, get_measure_value, contains_required_items

CRAWL_SUCCESS = Crawl(
    CrawlId="Id1",
    State="COMPLETED",
    StartTime=datetime(2024, 10, 1, 12, 0, 0),
    EndTime=datetime(2024, 10, 1, 12, 3, 0),
    # ErrorMessage=,
    DPUHour=0.475,
    Summary="""{\"TABLE\":{\"ADD\":\"{\\\"Details\\\":{\\\"names\\\":[\\\"success\\\"]},\\\"Count\\\":1}\"},\"PARTITION\":{\"ADD\":\"{\\\"Details\\\"
:{\\\"success\\\":[\\\"table_good\\\"]},\\\"Count\\\":1}\"}}""",
)

CRAWL_FAILURE = Crawl(
    CrawlId="Id2",
    State="FAILED",
    StartTime=datetime(2024, 10, 1, 12, 10, 0),
    EndTime=datetime(2024, 10, 1, 12, 13, 0),
    ErrorMessage="Service Principal: glue.amazonaws.com is not authorized to perform: glue:CreateTable on resource: arn:aws:glue:eu-central-1...",
    DPUHour=0.475,
)

CRAWL_RUNNING = Crawl(
    CrawlId="Id3",
    State="RUNNING",
    StartTime=datetime(2024, 10, 1, 12, 20, 0),
    DPUHour=0.475,
)


####################################################################
# here we check number of records returned and fields (dimensions and metric values)
def test_two_completed_jobs_records_integrity(boto3_client_creator):
    # explicitly return 2 good records
    with patch(
        "lib.metrics_extractor.glue_crawlers_metrics_extractor.GlueManager.get_crawls"
    ) as mocked_get_crawls:
        mocked_get_crawls.return_value = [CRAWL_SUCCESS, CRAWL_FAILURE]

        extractor = GlueCrawlersMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name="glue_crawler1",
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["crawl_id"]
        required_metrics = [
            "execution",
            "succeeded",
            "failed",
            "error_message",
            "dpu_seconds",
        ]

        record_in_scope = records[0]

        mocked_get_crawls.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be three glue crawler run record"  # we got both records
        assert contains_required_items(
            record_in_scope, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_in_scope, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


# here we check number of records returned
def test_skip_running_job(boto3_client_creator):
    # explicitly return 2 records - 1 completed, 1 running
    with patch(
        "lib.metrics_extractor.glue_crawlers_metrics_extractor.GlueManager.get_crawls"
    ) as mocked_get_crawls:
        mocked_get_crawls.return_value = [CRAWL_SUCCESS, CRAWL_RUNNING]

        extractor = GlueCrawlersMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name="glue_job1",
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        mocked_get_crawls.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 1
        ), "There should be just one glue job run record"  # we only take completed jobs

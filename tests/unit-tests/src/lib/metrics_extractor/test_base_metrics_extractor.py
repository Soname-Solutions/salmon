from datetime import datetime

from lib.metrics_extractor import BaseMetricsExtractor
from common import boto3_client_creator
from unittest.mock import patch

TIMESTREAM_QUERY_RUNNER_CLASS_NAME = (
    "lib.metrics_extractor.base_metrics_extractor.TimeStreamQueryRunner"
)


class ConcreteMetricsExtractor(BaseMetricsExtractor):
    def prepare_metrics_data(self, since_time: datetime):
        return [], {}


def test_get_aws_service_client(boto3_client_creator):
    extractor = ConcreteMetricsExtractor(
        boto3_client_creator=boto3_client_creator,
        aws_client_name="glue",
        resource_name="glue_job1",
        monitored_environment_name="env1",
    )

    client = extractor.get_aws_service_client()
    assert client.meta.service_model.service_name == "glue"

    client = extractor.get_aws_service_client("s3")
    assert client.meta.service_model.service_name == "s3"

# TODO: when implementing these tests
# 1. check send_alerts method for each resource_type
#  glue_workflows and lambda_functions should have this attribute, others - shouldn't

from lib.metrics_extractor import MetricsExtractorProvider
from common import boto3_client_creator
from lib.core.constants import SettingConfigResourceTypes as types
import pytest


def test_glue_jobs_provider(boto3_client_creator):
    extractor = MetricsExtractorProvider.get_metrics_extractor(
        types.GLUE_JOBS,
        monitored_environment_name="env1",
        resource_name="glue-job-1",
        aws_client_name="glue",
        boto3_client_creator=boto3_client_creator,
    )

    assert "GlueJobsMetricExtractor" in str(type(extractor))
    assert not hasattr(
        extractor, "send_alerts"
    ), "Extractor should not have a 'send_alerts' method"


def test_glue_workflows_provider(boto3_client_creator):
    extractor = MetricsExtractorProvider.get_metrics_extractor(
        types.GLUE_WORKFLOWS,
        monitored_environment_name="env1",
        resource_name="glue-wf-1",
        aws_client_name="glue",
        boto3_client_creator=boto3_client_creator,
    )

    assert "GlueWorkflowsMetricExtractor" in str(type(extractor))
    assert hasattr(
        extractor, "send_alerts"
    ), "Extractor should have a 'send_alerts' method"


def test_wrong_resource_type_provider(boto3_client_creator):
    with pytest.raises(ValueError):
        extractor = MetricsExtractorProvider.get_metrics_extractor(
            "AWS_IMAGINARY_RESOURCE_TYPE",
            monitored_environment_name="env1",
            resource_name="glue-crawler-1",
            aws_client_name="glue",
            boto3_client_creator=boto3_client_creator,
        )


def test_lambda_functions_provider(boto3_client_creator):
    extractor = MetricsExtractorProvider.get_metrics_extractor(
        types.LAMBDA_FUNCTIONS,
        monitored_environment_name="env1",
        resource_name="lambda-1",
        aws_client_name="lambda",
        boto3_client_creator=boto3_client_creator,
    )

    assert "LambdaFunctionsMetricExtractor" in str(type(extractor))
    assert hasattr(
        extractor, "send_alerts"
    ), "Extractor should have a 'send_alerts' method"

    #   # we DON'T have upd time for this glue job in LAST_UPDATE_TIMES_SAMPLE

    # timestream_writer = mock_timestream_writer
    # timestream_metrics_table_name = "test_table_name"

    # result = process_individual_resource(
    #     monitored_environment_name=monitored_environment_name,
    #     resource_type=resource_type,
    #     resource_name=resource_name,
    #     boto3_client_creator=boto3_client_creator,
    #     aws_client_name=SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
    #         resource_type
    #     ],
    #     timestream_writer=timestream_writer,
    #     timestream_metrics_db_name=timestream_metrics_db_name,
    #     timestream_metrics_table_name=timestream_metrics_table_name,
    #     last_update_times=LAST_UPDATE_TIMES_SAMPLE,
    #     alerts_event_bus_name=alerts_event_bus_name,
    # )

    #     boto3_client_creator: boto3_client_creator,
    #     aws_client_name: str,
    #     resource_name: str,
    #     monitored_environment_name: str,
    #     timestream_db_name: str,
    #     timestream_metrics_table_name: str,

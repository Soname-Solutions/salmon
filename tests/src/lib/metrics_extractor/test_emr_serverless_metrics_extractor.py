from datetime import datetime
from unittest.mock import patch, MagicMock, call
from lib.metrics_extractor import EMRServerlessMetricExtractor
from lib.aws.emr_manager import (
    EMRJobRunData,
    ResourceUtilization,
    JobDriver,
    SparkSubmit,
)
from common import (
    boto3_client_creator,
    get_measure_value,
    get_dimension_value,
    contains_required_items,
)

EMR_APP_NAME = "emr-app-test"
EMR_APP_ID = "00fkm6vigfuq6215"
JOB_NAME = "emr-job-test"
JOB_ID_SUCCESS = "00flkba402s3b817"
JOB_ID_ERROR = "00fljue4c582dg17"
EMR_MANAGER_CLASS_NAME = (
    "lib.metrics_extractor.emr_serverless_metrics_extractor.EMRManager"
)
GET_EXECUTIONS_METHOD_NAME = f"{EMR_MANAGER_CLASS_NAME}.get_job_run"

JOB_RUN_SUCCESS = EMRJobRunData(
    applicationId=EMR_APP_ID,
    jobRunId=JOB_ID_SUCCESS,
    name=JOB_NAME,
    createdAt=datetime(2024, 1, 1, 0, 0, 0),
    updatedAt=datetime(2024, 1, 1, 0, 5, 0),
    state="SUCCESS",
    jobDriver=JobDriver(
        sparkSubmit=SparkSubmit(entryPoint="s3://s3-bucket/sample_spark_job.py")
    ),
    totalResourceUtilization=ResourceUtilization(
        vCPUHour="0.049", memoryGBHour="0.192", storageGBHour="0.231"
    ),
    totalExecutionDurationSeconds=45,
    billedResourceUtilization=ResourceUtilization(
        vCPUHour="0.068", memoryGBHour="0.268", storageGBHour="0.1"
    ),
)

JOB_RUN_ERROR = EMRJobRunData(
    applicationId=EMR_APP_ID,
    jobRunId=JOB_ID_ERROR,
    name=JOB_NAME,
    createdAt=datetime(2024, 1, 1, 0, 0, 0),
    updatedAt=datetime(2024, 1, 1, 0, 5, 0),
    state="FAILED",
    stateDetails="Job failed, please check complete logs in configured logging destination. ExitCode: 1.",
    jobDriver=JobDriver(
        sparkSubmit=SparkSubmit(entryPoint="s3://s3-bucket/sample_spark_job.py")
    ),
    totalResourceUtilization=ResourceUtilization(
        vCPUHour="0.048", memoryGBHour="0.191", storageGBHour="0.239"
    ),
    totalExecutionDurationSeconds=42,
    billedResourceUtilization=ResourceUtilization(
        vCPUHour="0.067", memoryGBHour="0.267", storageGBHour="0.0"
    ),
)


# ####################################################################
def setup_mock_emr_client(job_runs):
    mock_emr_client = MagicMock()
    mock_emr_client.list_applications.return_value = {
        "applications": [{"name": EMR_APP_NAME, "id": EMR_APP_ID}]
    }
    mock_emr_client.list_job_runs.return_value = {"jobRuns": job_runs}
    return mock_emr_client


def test_two_completed_records_integrity(boto3_client_creator):
    # mock emr client with two job runs returned by list_job_runs
    mock_emr_client = setup_mock_emr_client(
        job_runs=[{"id": JOB_ID_SUCCESS}, {"id": JOB_ID_ERROR}]
    )

    with patch("boto3.client", return_value=mock_emr_client), patch(
        GET_EXECUTIONS_METHOD_NAME
    ) as mocked_get_executions:
        # get_job_run should return EMRJobRunData for each job correspondingly
        mocked_get_executions.side_effect = [
            JOB_RUN_SUCCESS,
            JOB_RUN_ERROR,
        ]

        extractor = EMRServerlessMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="emr-serverless",
            resource_name=EMR_APP_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(since_time=since_time)

        required_dimensions = ["job_run_id"]
        required_metrics = [
            "job_run_name",
            "app_id",
            "execution",
            "succeeded",
            "failed",
            "execution_time_sec",
            "error_message",
            "total_vCPU_hour",
            "total_memory_GB_hour",
            "total_storage_GB_hour",
            "billed_vCPU_hour",
            "billed_memory_GB_hour",
            "billed_storage_GB_hour",
        ]

        expected_calls = [
            call(app_id=EMR_APP_ID, run_id=JOB_ID_SUCCESS),
            call(app_id=EMR_APP_ID, run_id=JOB_ID_ERROR),
        ]

        mocked_get_executions.assert_has_calls(
            expected_calls
        )  # get_job_run should be called for each JOB ID

        assert len(records) == 2, "There should be just two execution records"

        assert contains_required_items(
            records[0], "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            records[0], "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


def test_failed_job_run(boto3_client_creator):
    # mock emr client with one failed job run returned by list_job_runs
    mock_emr_client = setup_mock_emr_client(job_runs=[{"id": JOB_ID_ERROR}])

    with patch("boto3.client", return_value=mock_emr_client), patch(
        GET_EXECUTIONS_METHOD_NAME
    ) as mocked_get_executions:
        # get_job_run should return EMRJobRunData correspondingly
        mocked_get_executions.return_value = JOB_RUN_ERROR

        extractor = EMRServerlessMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="emr-serverless",
            resource_name=EMR_APP_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(since_time=since_time)

        mocked_get_executions.assert_called_once()
        assert len(records) == 1, "There should be one execution record"
        assert get_dimension_value(records[0], "job_run_id") == JOB_ID_ERROR
        assert get_measure_value(records[0], "job_run_name") == JOB_NAME
        assert get_measure_value(records[0], "app_id") == EMR_APP_ID
        assert get_measure_value(records[0], "execution") == "1"
        assert get_measure_value(records[0], "succeeded") == "0"
        assert get_measure_value(records[0], "failed") == "1"  # error
        assert get_measure_value(records[0], "execution_time_sec") == "42"
        assert (
            get_measure_value(records[0], "error_message") == "ExitCode: 1."
        )  # error message assigned as expected
        assert get_measure_value(records[0], "total_vCPU_hour") == "0.048"
        assert get_measure_value(records[0], "total_memory_GB_hour") == "0.191"
        assert get_measure_value(records[0], "total_storage_GB_hour") == "0.239"
        assert get_measure_value(records[0], "billed_vCPU_hour") == "0.067"
        assert get_measure_value(records[0], "billed_memory_GB_hour") == "0.267"
        assert get_measure_value(records[0], "billed_storage_GB_hour") == "0.0"


def test_success_job_run(boto3_client_creator):
    # mock emr client with one success job run returned by list_job_runs
    mock_emr_client = setup_mock_emr_client(job_runs=[{"id": JOB_ID_SUCCESS}])

    with patch("boto3.client", return_value=mock_emr_client), patch(
        GET_EXECUTIONS_METHOD_NAME
    ) as mocked_get_executions:
        # get_job_run should return EMRJobRunData correspondingly
        mocked_get_executions.return_value = JOB_RUN_SUCCESS

        extractor = EMRServerlessMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="emr-serverless",
            resource_name=EMR_APP_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(since_time=since_time)

        mocked_get_executions.assert_called_once()
        assert len(records) == 1, "There should be one execution record"
        assert get_dimension_value(records[0], "job_run_id") == JOB_ID_SUCCESS
        assert get_measure_value(records[0], "job_run_name") == JOB_NAME
        assert get_measure_value(records[0], "app_id") == EMR_APP_ID
        assert get_measure_value(records[0], "execution") == "1"
        assert get_measure_value(records[0], "succeeded") == "1"  # success
        assert get_measure_value(records[0], "failed") == "0"
        assert get_measure_value(records[0], "execution_time_sec") == "45"
        assert (
            get_measure_value(records[0], "error_message") == "None"
        )  # no error message as expected
        assert get_measure_value(records[0], "total_vCPU_hour") == "0.049"
        assert get_measure_value(records[0], "total_memory_GB_hour") == "0.192"
        assert get_measure_value(records[0], "total_storage_GB_hour") == "0.231"
        assert get_measure_value(records[0], "billed_vCPU_hour") == "0.068"
        assert get_measure_value(records[0], "billed_memory_GB_hour") == "0.268"
        assert get_measure_value(records[0], "billed_storage_GB_hour") == "0.1"


def test_no_job_runs(boto3_client_creator):
    # mock emr client with no job runs returned by list_job_runs
    mock_emr_client = setup_mock_emr_client(job_runs=[])

    with patch("boto3.client", return_value=mock_emr_client), patch(
        GET_EXECUTIONS_METHOD_NAME
    ) as mocked_get_executions:
        extractor = EMRServerlessMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="emr-serverless",
            resource_name=EMR_APP_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(since_time=since_time)

        # get_job_run shouldn't be called since no Job IDs returned
        mocked_get_executions.assert_not_called()
        assert len(records) == 0, "There shouldn't be records"

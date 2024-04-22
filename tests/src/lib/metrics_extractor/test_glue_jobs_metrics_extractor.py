from datetime import datetime

from lib.metrics_extractor import GlueJobsMetricExtractor
from lib.aws.glue_manager import JobRun
from lib.aws import Boto3ClientCreator
from unittest.mock import patch
import pytest

JOB_RUN_COMPLETED_WITH_DPU = JobRun(
    Id="jr_5b243dd35200b06be1f1858746876c06e68d85a7164697a64e3d0f6b0a5da420",
    Attempt=0,
    JobName="glue_job1",
    StartedOn=datetime(2024, 4, 19, 15, 5, 37, 287000),
    LastModifiedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    CompletedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    JobRunState="SUCCEEDED",
    PredecessorRuns=[],
    AllocatedCapacity=2,
    ExecutionTime=41,
    Timeout=2880,
    MaxCapacity=2.0,
    WorkerType="G.1X",
    NumberOfWorkers=2,
    LogGroupName="/aws-glue/jobs",
    GlueVersion="3.0",
    DPUSeconds=120.0,
)

JOB_RUN_COMPLETED_WITHOUT_DPU = JobRun(
    Id="jr_5b243dd35200b06be1f1858746876c06e68d85a7164697a64e3d0f6b0a5da420",
    Attempt=0,
    JobName="glue_job1",
    StartedOn=datetime(2024, 4, 19, 15, 5, 37, 287000),
    LastModifiedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    CompletedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    JobRunState="FAILED",
    ErrorMessage="Some error message",
    PredecessorRuns=[],
    AllocatedCapacity=2,
    ExecutionTime=41,
    Timeout=2880,
    MaxCapacity=2.0,
    WorkerType="G.1X",
    NumberOfWorkers=2,
    LogGroupName="/aws-glue/jobs",
    GlueVersion="3.0",
)

JOB_RUN_ERROR = JobRun(
    Id="jr_5b243dd35200b06be1f1858746876c06e68d85a7164697a64e3d0f6b0a5da420",
    Attempt=0,
    JobName="glue_job1",
    StartedOn=datetime(2024, 4, 19, 15, 5, 37, 287000),
    LastModifiedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    CompletedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    JobRunState="FAILED",
    ErrorMessage="Some error message",
    PredecessorRuns=[],
    AllocatedCapacity=2,
    ExecutionTime=41,
    Timeout=2880,
    MaxCapacity=2.0,
    WorkerType="G.1X",
    NumberOfWorkers=2,
    LogGroupName="/aws-glue/jobs",
    GlueVersion="3.0",
    DPUSeconds=120.0,
)

JOB_RUN_RUNNING = JobRun(
    Id="jr_5b243dd35200b06be1f1858746876c06e68d85a7164697a64e3d0f6b0a5da420",
    Attempt=0,
    JobName="glue_job1",
    StartedOn=datetime(2024, 4, 19, 15, 5, 37, 287000),
    LastModifiedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    CompletedOn=datetime(2024, 4, 19, 15, 6, 25, 701000),
    JobRunState="RUNNING",
    PredecessorRuns=[],
    AllocatedCapacity=2,
    ExecutionTime=41,
    Timeout=2880,
    MaxCapacity=2.0,
    WorkerType="G.1X",
    NumberOfWorkers=2,
    LogGroupName="/aws-glue/jobs",
    GlueVersion="3.0",
    DPUSeconds=120.0,
)

####################################################################

@pytest.fixture(scope="module")
def boto3_client_creator():
    return Boto3ClientCreator("1234567890", "us-east-1")

####################################################################

def contains_required_items(record, ts_record_subkey, required_items):
    record_items = [x["Name"] for x in record[ts_record_subkey]]
    for dimension in required_items:
        if dimension not in record_items:
            return False

    return True

def get_measure_value(record, metric_name):
    measure_data = record['MeasureValues']
    for measure in measure_data:
        if measure['Name'] == metric_name:
            return measure['Value']
        
    return None


# here we check number of records returned and fields (dimensions and metric values)
def test_two_completed_jobs_records_integrity(boto3_client_creator):

    # explicitly return 2 good records
    with patch("lib.metrics_extractor.glue_jobs_metrics_extractor.GlueManager.get_job_runs") as instance:
        instance.return_value = [
            JOB_RUN_COMPLETED_WITH_DPU,
            JOB_RUN_COMPLETED_WITHOUT_DPU,
            JOB_RUN_ERROR
        ]

        extractor = GlueJobsMetricExtractor(
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

        required_dimensions = ["job_run_id"]
        required_metrics = [
            "execution",
            "succeeded",
            "failed",
            "execution_time_sec",
            "error_message",
            "dpu_seconds",
        ]

        record_in_scope = records[0]

        instance.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 3
        ), "There should be three glue job run record"  # we got both records
        assert contains_required_items(
            record_in_scope, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_in_scope, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


# here we check number of records returned and fields (dimensions and metric values)
def test_skip_running_job(boto3_client_creator):

    # explicitly return 2 good records
    with patch("lib.metrics_extractor.glue_jobs_metrics_extractor.GlueManager.get_job_runs") as instance:
        instance.return_value = [
            JOB_RUN_COMPLETED_WITH_DPU,
            JOB_RUN_RUNNING,
        ]

        extractor = GlueJobsMetricExtractor(
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

        instance.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 1
        ), "There should be just one glue job run record"  # we only take completed jobs

# here we check if we provide proper dpu_seconds value - either from glue output, or calculating ourselves when needed
def test_dpu_seconds_calculated(boto3_client_creator):

    # explicitly return 2 good records
    with patch("lib.metrics_extractor.glue_jobs_metrics_extractor.GlueManager.get_job_runs") as instance:
        instance.return_value = [
            JOB_RUN_COMPLETED_WITH_DPU,
            JOB_RUN_COMPLETED_WITHOUT_DPU,
        ]

        extractor = GlueJobsMetricExtractor(
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

        instance.assert_called_once()  # mocked call executed as expected
        assert (
            len(records) == 2
        ), "There should be two glue job run record"  # we only take completed jobs

        dpu_rec_1 = get_measure_value(records[0], "dpu_seconds")
        dpu_rec_1_expected = JOB_RUN_COMPLETED_WITH_DPU.DPUSeconds
        assert str(dpu_rec_1) == str(dpu_rec_1_expected), "Record 1: DPU seconds should be taken from output"

        dpu_rec_2 = get_measure_value(records[1], "dpu_seconds")
        dpu_rec_2_expected = float(JOB_RUN_COMPLETED_WITHOUT_DPU.MaxCapacity) * JOB_RUN_COMPLETED_WITHOUT_DPU.ExecutionTime
        assert str(dpu_rec_2) == str(dpu_rec_2_expected), "Record 2: DPU seconds should be calculated properly"
import pytest

from datetime import datetime, timedelta, timezone

from lib.aws.emr_manager import EMRManager, EMRJobRunData, ResourceUtilization

cur_time = datetime.now().astimezone(timezone.utc) - timedelta(minutes=10)

JOB_RUN_PENDING = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun_pending1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="PENDING",
)

JOB_RUN_COMPLETED = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun_completed1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="SUCCESS",
    totalResourceUtilization=ResourceUtilization(
        vCPUHour=1.0, memoryGBHour=1.0, storageGBHour=1.0
    ),
    billedResourceUtilization=ResourceUtilization(
        vCPUHour=1.0, memoryGBHour=1.0, storageGBHour=1.0
    ),
)

JOB_RUN_COMPLETED_NO_RESOURCE_UTILIZATION = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun_completed_no_resource_utilization1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="SUCCESS",
)


@pytest.mark.parametrize(
    ("job_run_data, is_final_state"),
    [
        (JOB_RUN_PENDING, False),
        (JOB_RUN_COMPLETED, True),
        (JOB_RUN_COMPLETED_NO_RESOURCE_UTILIZATION, False),
    ],
)
def test_is_final_state(job_run_data: EMRJobRunData, is_final_state: bool):
    assert (
        job_run_data.is_final_state == is_final_state
    ), f"For jobrun {job_run_data.jobRunId}, is_final_state should be {is_final_state}"

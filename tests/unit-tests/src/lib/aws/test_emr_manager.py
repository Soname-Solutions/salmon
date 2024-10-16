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

JOB_RUN_FAILED = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun_completed1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="FAILED",
    totalResourceUtilization=ResourceUtilization(
        vCPUHour=1.0, memoryGBHour=1.0, storageGBHour=1.0
    ),
    billedResourceUtilization=ResourceUtilization(
        vCPUHour=1.0, memoryGBHour=1.0, storageGBHour=1.0
    ),
    stateDetails="Ahtung, error!",
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
    (
        "job_run_data, is_final_state, is_success, is_failure, is_resourceutilization_populated, error_message_empty"
    ),
    [
        (JOB_RUN_PENDING, False, False, False, False, True),
        (JOB_RUN_COMPLETED, True, True, False, True, True),
        (JOB_RUN_FAILED, True, False, True, True, False),
        (JOB_RUN_COMPLETED_NO_RESOURCE_UTILIZATION, False, True, False, False, True),
    ],
)
def test_properties(
    job_run_data: EMRJobRunData,
    is_final_state: bool,
    is_success: bool,
    is_failure: bool,
    is_resourceutilization_populated: bool,
    error_message_empty: bool,
):
    assert (
        job_run_data.is_final_state == is_final_state
    ), f"For jobrun {job_run_data.jobRunId}, is_final_state should be {is_final_state}"

    assert (
        job_run_data.IsSuccess == is_success
    ), f"For jobrun {job_run_data.jobRunId}, IsSuccess should be {is_success}"
    assert (
        job_run_data.IsFailure == is_failure
    ), f"For jobrun {job_run_data.jobRunId}, IsFailure should be {is_failure}"
    assert (
        job_run_data.is_ResourceUtilization_populated
        == is_resourceutilization_populated
    ), f"For jobrun {job_run_data.jobRunId}, is_ResourceUtilization_populated should be {is_resourceutilization_populated}"

    is_error_message_empty = (job_run_data.ErrorMessage is None) or (
        job_run_data.ErrorMessage == ""
    )

    assert (
        is_error_message_empty == error_message_empty
    ), f"For jobrun {job_run_data.jobRunId}, error_message should be {'empty' if error_message_empty else 'not empty'}. Actual error_message: {job_run_data.ErrorMessage}"

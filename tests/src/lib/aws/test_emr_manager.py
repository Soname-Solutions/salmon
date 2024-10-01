from datetime import datetime, timedelta, timezone

from lib.aws.emr_manager import EMRManager, EMRJobRunData, ResourceUtilization

cur_time = datetime.now().astimezone(timezone.utc) - timedelta(minutes=10)

JOB_RUN_PENDING = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="PENDING",
)

JOB_RUN_COMPLETED = EMRJobRunData(
    applicationId="app1",
    jobRunId="jobrun1",
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
    jobRunId="jobrun1",
    name="job1",
    createdAt=cur_time,
    updatedAt=cur_time,
    state="SUCCESS",
)

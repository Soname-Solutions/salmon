import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from lib.event_mapper import EMRServerlessEventMapper, EMRServerlessEventMapperException
from lib.core.constants import SettingConfigResourceTypes as types

EVENT_TYPE = "EMR Serverless Job Run State Change"
EMR_APP_NAME = "emr-app-test"
EMR_APP_ID = "00fkm6vigfuq6215"
JOB_NAME = "emr-job-test"
JOB_RUN = {
    "jobRun": {
        "applicationId": EMR_APP_ID,
        "jobRunId": "00flfo8g80vlko17",
        "createdAt": str(datetime(2000, 1, 1, 0, 0, 0)),
        "updatedAt": str(datetime(2000, 1, 1, 1, 0, 0)),
        "state": "FAILED",
        "stateDetails": "Job failed",
        "jobDriver": {
            "sparkSubmit": {
                "entryPoint": "s3://s3-salmonts-emr-scripts-dev/job2_failure.py"
            }
        },
    }
}


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


@pytest.fixture(scope="function", autouse=True)
def mock_emr_client():
    mock_emr_client = MagicMock()
    mock_emr_client.get_application.return_value = {
        "application": {"name": EMR_APP_NAME}
    }
    mock_emr_client.get_job_run.return_value = JOB_RUN
    with patch("boto3.client", return_value=mock_emr_client) as mock_emr:
        yield mock_emr


def get_emr_serverless_event(event_state="SUCCESS", detail_type=EVENT_TYPE):
    return {
        "detail-type": detail_type,
        "source": "aws.emr-serverless",
        "account": "1234567890",
        "time": str(datetime(2000, 1, 1, 0, 0, 0)),
        "region": "test-region",
        "detail": {
            "jobRunId": "1234567890",
            "jobRunName": JOB_NAME,
            "applicationId": EMR_APP_ID,
            "state": event_state,
        },
    }


def test_get_resource_name_success(mock_settings, mock_emr_client):
    event = get_emr_serverless_event()
    mapper = EMRServerlessEventMapper(
        resource_type=types.EMR_SERVERLESS, event=event, settings=mock_settings
    )
    assert mapper.get_resource_name() == EMR_APP_NAME


def test_get_resource_name_exception(mock_settings, mock_emr_client):
    event = get_emr_serverless_event()
    # remove app id from the event
    del event["detail"]["applicationId"]

    mapper = EMRServerlessEventMapper(
        resource_type=types.EMR_SERVERLESS, event=event, settings=mock_settings
    )
    with pytest.raises(
        EMRServerlessEventMapperException,
        match=f"EMR Serverless Application ID is not defined in the event:",
    ):
        mapper.get_resource_name()


def test_get_run_id_exception(mock_settings, mock_emr_client):
    event = get_emr_serverless_event()
    # remove run id from the event
    del event["detail"]["jobRunId"]

    mapper = EMRServerlessEventMapper(
        resource_type=types.EMR_SERVERLESS, event=event, settings=mock_settings
    )
    with pytest.raises(
        EMRServerlessEventMapperException,
        match=f"EMR Job Run ID is not defined in the event:",
    ):
        mapper.get_message_body()


def test_get_execution_info_url(mock_settings, mock_emr_client):
    expected_url = (
        "https://test-region.console.aws.amazon.com/emr?region=test-region#/serverless"
    )
    event = get_emr_serverless_event()
    mapper = EMRServerlessEventMapper(
        resource_type=types.EMR_SERVERLESS, event=event, settings=mock_settings
    )
    returned_url = mapper.get_execution_info_url(resource_name=EMR_APP_NAME)

    assert returned_url == expected_url


def test_get_message_body(mock_settings, mock_emr_client):
    event = get_emr_serverless_event()
    mapper = EMRServerlessEventMapper(
        resource_type=types.EMR_SERVERLESS, event=event, settings=mock_settings
    )

    returned_message_body = mapper.get_message_body()
    returned_table_rows = returned_message_body[0]["table"]["rows"]
    expected_table_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", str(datetime(2000, 1, 1, 0, 0, 0))]},
        {"values": ["Event Type", EVENT_TYPE]},
        {"values": ["EMR Serverless Application Name", EMR_APP_NAME]},
        {"values": ["State", "SUCCESS"]},
        {"values": ["Job Run ID", "1234567890"]},
        {
            "values": [
                "Script Location",
                "s3://s3-salmonts-emr-scripts-dev/job2_failure.py",
            ]
        },
        {
            "values": [
                "Console URL",
                "<a href='https://test-region.console.aws.amazon.com/emr?region=test-region#/serverless'>Link to Amazon EMR Console</a>",
            ]
        },
        {"values": ["Message", "Job failed"]},
    ]

    assert returned_table_rows == expected_table_rows

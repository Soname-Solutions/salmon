import pytest
from unittest.mock import patch
from datetime import datetime

from lib.event_mapper import GeneralAwsEventMapper, ExecutionInfoUrlMixin
from lib.core.constants import SettingConfigResourceTypes as types, EventResult

TEST_EVENT = {
    "source": "aws.glue",
    "time": str(datetime(2000, 1, 1, 0, 0, 0)),
    "detail-type": "Glue Job State Change",
    "account": "1234567890",
    "region": "test-region",
    "detail": {"name": "glue-test", "state": "Failed", "jobRunId": "123456789"},
}


@pytest.fixture(scope="module")
def mock_settings():
    with patch("lib.settings.settings") as mocked_settings:
        mocked_settings.get_monitored_environment_name.return_value = "Test Env"
        yield mocked_settings


class ConcreteAwsEventMapper(GeneralAwsEventMapper):
    def get_resource_name(self):
        return self.event["detail"]["name"]

    def get_resource_state(self):
        return self.event["detail"]["state"]

    def get_event_result(self):
        return EventResult.FAILURE

    def get_execution_info_url(self, resource_name: str):
        return ExecutionInfoUrlMixin.get_url(
            resource_type=self.resource_type,
            region_name=self.event["region"],
            resource_name=resource_name,
            run_id=self.event["detail"]["jobRunId"],
        )

    def get_message_body(self):
        message_body, _ = super().create_message_body_with_common_rows()
        return message_body


def test_event_mapper_to_message(mock_settings):
    event_mapper = ConcreteAwsEventMapper(
        resource_type=types.GLUE_JOBS, event=TEST_EVENT, settings=mock_settings
    )
    returned_message = event_mapper.to_message()

    expected_rows = [
        {"values": ["AWS Account", "1234567890"]},
        {"values": ["AWS Region", "test-region"]},
        {"values": ["Time", "2000-01-01 00:00:00"]},
        {"values": ["Event Type", "Glue Job State Change"]},
    ]

    assert (
        returned_message["message_subject"]
        == "Test Env: Failed - glue_jobs : glue-test"
    )
    assert returned_message["message_body"][0]["table"]["rows"] == expected_rows
    assert event_mapper.get_event_result() == EventResult.FAILURE
    assert (
        event_mapper.get_execution_info_url("glue-test")
        == "https://test-region.console.aws.amazon.com/gluestudio/home?region=test-region#/job/glue-test/run/123456789"
    )


def test_event_mapper_exception(mock_settings):
    resource_type = "test-resource-type"
    event_mapper = ConcreteAwsEventMapper(
        resource_type=resource_type, event=TEST_EVENT, settings=mock_settings
    )
    with pytest.raises(
        KeyError,
        match=f"Execution link is not generated for the resource type {resource_type}",
    ):
        event_mapper.get_execution_info_url("glue-test")

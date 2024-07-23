from datetime import datetime

import pytest

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lib.metrics_extractor import (
    retrieve_last_update_time_for_all_resources,
    get_last_update_time,
    get_earliest_last_update_time_for_resource_set,
    MetricsExtractorException,
)
from unittest.mock import MagicMock
from unittest.mock import patch

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)


###############################################################################

EARLIEST_WRITABLE_TIME = datetime(2000, 1, 1, 0, 0, 0)


@pytest.fixture(scope="module")
def last_update_time_sample_data():
    return {
        "glue_jobs": [
            {
                "resource_name": "glue-job-1",
                "last_update_time": "2024-01-09 11:00:40.911000000",
            },
            {
                "resource_name": "glue-job-2",
                "last_update_time": "2024-01-10 12:00:00.143000000",
            },
        ],
        "glue_workflows": [
            {
                "resource_name": "workflow-1",
                "last_update_time": "2024-01-11 13:00:00.256000000",
            }
        ],
    }


@pytest.fixture(scope="function")
def mock_timestream_writer():
    mocked_timestream_writer = MagicMock()
    mocked_timestream_writer.get_earliest_writeable_time_for_table.return_value = (
        EARLIEST_WRITABLE_TIME
    )

    with patch(
        "lambda_extract_metrics.TimestreamTableWriter", mocked_timestream_writer
    ) as mock_get_extractor:
        yield mocked_timestream_writer


###############################################################################


def test_retrieve_last_update_time_empty():
    class MockedTimestreamQueryRunner:
        def is_table_empty(self, database_name, table_name):
            return True

    mocked_timestream_query_runner = MockedTimestreamQueryRunner()
    timestream_db_name = "sample_db_name"
    result = retrieve_last_update_time_for_all_resources(
        mocked_timestream_query_runner, timestream_db_name, logger
    )

    assert result == {}


def test_retrieve_last_update_time_glue():
    class MockedTimestreamQueryRunner:
        def is_table_empty(self, database_name, table_name):
            return not ("glue" in table_name)

        def execute_query(self, query):
            outp = [
                {
                    "resource_type": "glue_jobs",
                    "resource_name": "resource1",
                    "last_update_time": "2024-01-09 11:00:40.911000000",
                },
                {
                    "resource_type": "glue_workflows",
                    "resource_name": "resource3",
                    "last_update_time": "2024-01-10 12:00:00.143000000",
                },
                {
                    "resource_type": "glue_jobs",
                    "resource_name": "resource2",
                    "last_update_time": "2024-01-10 12:00:00.143000000",
                },
            ]
            return outp

    mocked_timestream_query_runner = MockedTimestreamQueryRunner()
    timestream_db_name = "sample_db_name"
    result = retrieve_last_update_time_for_all_resources(
        mocked_timestream_query_runner, timestream_db_name, logger
    )

    # source data to be grouped by resource type
    expected_result = {
        "glue_jobs": [
            {
                "resource_name": "resource1",
                "last_update_time": "2024-01-09 11:00:40.911000000",
            },
            {
                "resource_name": "resource2",
                "last_update_time": "2024-01-10 12:00:00.143000000",
            },
        ],
        "glue_workflows": [
            {
                "resource_name": "resource3",
                "last_update_time": "2024-01-10 12:00:00.143000000",
            }
        ],
    }

    assert result == expected_result


def test_retrieve_last_update_time_db_error():
    class MockedTimestreamQueryRunner:
        def is_table_empty(self, database_name, table_name):
            return not ("glue" in table_name)

        def execute_query(self, query):
            raise Exception("Can't connect to DB")

    mocked_timestream_query_runner = MockedTimestreamQueryRunner()
    timestream_db_name = "sample_db_name"

    with pytest.raises(MetricsExtractorException):
        result = retrieve_last_update_time_for_all_resources(
            mocked_timestream_query_runner, timestream_db_name, logger
        )


###############################################################################


def test_get_last_update_time_none_input():
    assert get_last_update_time(None, "glue_jobs", "glue-job-1") is None


def test_get_last_update_time_empty_input():
    assert get_last_update_time({}, "glue_jobs", "glue-job-1") is None


def test_get_last_update_time_no_resource_type(last_update_time_sample_data):
    assert (
        get_last_update_time(
            last_update_time_sample_data, "step_functions", "step-function-1"
        )
        is None
    )


def test_get_last_update_time_no_resource_name(last_update_time_sample_data):
    assert (
        get_last_update_time(
            last_update_time_sample_data, "glue_jobs", "nonexistent-job"
        )
        is None
    )


def test_get_last_update_time_valid_input(last_update_time_sample_data):
    expected_datetime = str_utc_datetime_to_datetime("2024-01-09 11:00:40.911000000")
    actual_datetime = get_last_update_time(
        last_update_time_sample_data, "glue_jobs", "glue-job-1"
    )
    assert actual_datetime == expected_datetime


@pytest.mark.parametrize(
    "scenario, last_update_times, resource_names, expected_date",
    [
        (
            "scen1",
            [
                {
                    "resource_name": "test-dq-ruleset-1",
                    "last_update_time": "2024-07-21 00:01:52.820000000",
                },
                {
                    "resource_name": "test-de-ruleset-2",
                    "last_update_time": "2024-07-22 00:01:56.042000000",
                },
            ],
            ["test-dq-ruleset-1", "test-de-ruleset-2"],
            # both resources have last_update_time assigned, so the earliest date should be returned
            str_utc_datetime_to_datetime("2024-07-21 00:01:52.820000000"),
        ),
        (
            "scen2",
            [
                {
                    "resource_name": "test-dq-ruleset-5",
                    "last_update_time": "2024-07-20 00:00:41.652000000",
                }
            ],
            ["test-dq-ruleset-2"],
            # this resource does not have last_update_time assigned, so earliest writable time should be returned
            EARLIEST_WRITABLE_TIME,
        ),
        (
            "scen3",
            [
                {
                    "resource_name": "test-dq-ruleset-1",
                    "last_update_time": "2024-07-20 00:00:41.652000000",
                },
                {
                    "resource_name": "test-dq-ruleset-2",
                    "last_update_time": "2024-07-21 00:01:52.820000000",
                },
                {
                    "resource_name": "test-de-ruleset-3",
                    "last_update_time": "2024-07-22 00:01:56.042000000",
                },
            ],
            ["test-de-ruleset-3"],
            # only one resource provided, so its last_update_time should be returned
            str_utc_datetime_to_datetime("2024-07-22 00:01:56.042000000"),
        ),
    ],
)
def test_get_earliest_last_update_time_for_resource_set(
    mock_timestream_writer, scenario, last_update_times, resource_names, expected_date
):
    returned_min_date = get_earliest_last_update_time_for_resource_set(
        last_update_times, resource_names, mock_timestream_writer
    )
    assert returned_min_date == expected_date, f"Date mismatch for scenario {scenario}"

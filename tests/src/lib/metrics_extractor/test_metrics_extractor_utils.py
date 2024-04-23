from datetime import datetime

import pytest

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lib.metrics_extractor import (
    retrieve_last_update_time_for_all_resources,
    get_last_update_time,
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

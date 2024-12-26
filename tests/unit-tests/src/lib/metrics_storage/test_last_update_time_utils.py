from datetime import datetime

import pytest

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lib.metrics_storage.timestream_metrics_storage import (
    TimestreamMetricsStorage,
    MetricsStorageException,
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


###############################################################################
# tests for retrieve_last_update_time_for_all_resources


# metric storage says "tables are empty" -> empty JSON
def test_retrieve_last_update_time_empty():
    db_name = "sample_db_name"
    metrics_storage = TimestreamMetricsStorage(db_name)

    with patch.object(TimestreamMetricsStorage, "is_table_empty", return_value=True):
        result = metrics_storage.retrieve_last_update_time_for_all_resources(logger)

    assert result == {}


# metric storage responds to glue only
# test how last_update_times are grouped
def test_retrieve_last_update_time_glue():
    db_name = "sample_db_name"
    metrics_storage = TimestreamMetricsStorage(db_name)

    def is_table_empty(table_name):
        print(f"Called with {table_name = }")
        return not ("glue" in table_name)

    def execute_query(query):
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

    with patch.object(
        TimestreamMetricsStorage, "is_table_empty", side_effect=is_table_empty
    ), patch.object(
        TimestreamMetricsStorage, "execute_query", side_effect=execute_query
    ):
        result = metrics_storage.retrieve_last_update_time_for_all_resources(logger)

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
    db_name = "sample_db_name"
    metrics_storage = TimestreamMetricsStorage(db_name)

    def is_table_empty(table_name):
        return not ("glue" in table_name)

    def execute_query(query):
        raise Exception("Can't connect to DB")

    with patch.object(
        TimestreamMetricsStorage, "is_table_empty", side_effect=is_table_empty
    ), patch.object(
        TimestreamMetricsStorage, "execute_query", side_effect=execute_query
    ):
        with pytest.raises(MetricsStorageException):
            result = metrics_storage.retrieve_last_update_time_for_all_resources(logger)


###############################################################################

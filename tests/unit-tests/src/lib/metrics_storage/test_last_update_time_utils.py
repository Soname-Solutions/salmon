from datetime import datetime

import pytest

from lib.core.datetime_utils import str_utc_datetime_to_datetime
from lib.metrics_storage.timestream_metrics_storage import (
    TimestreamMetricsStorage,
    MetricsStorageException,
)
from unittest.mock import MagicMock
from unittest.mock import patch

from lib.core.constants import SettingConfigResourceTypes as types


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


@pytest.fixture
def metrics_storage():
    db_name = "sample_db_name"
    metrics_storage = TimestreamMetricsStorage(db_name)
    return metrics_storage


###############################################################################
# tests for retrieve_last_update_time_for_all_resources


# metric storage says "tables are empty" -> empty JSON
def test_retrieve_last_update_time_empty(metrics_storage):
    with patch.object(TimestreamMetricsStorage, "is_table_empty", return_value=True):
        result = metrics_storage.retrieve_last_update_time_for_all_resources(logger)

    assert result == {}


# metric storage responds to glue only
# test how last_update_times are grouped
def test_retrieve_last_update_time_glue(metrics_storage):
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


def test_retrieve_last_update_time_db_error(metrics_storage):
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
# tests for get_resource_last_update_time_from_json


# JSON None -> res is empty
def test_get_last_update_time_none_input(metrics_storage):
    assert (
        metrics_storage.get_resource_last_update_time_from_json(
            None, "glue_jobs", "glue-job-1"
        )
        is None
    )


# JSON = {} -> res is empty
def test_get_last_update_time_empty_input(metrics_storage):
    assert (
        metrics_storage.get_resource_last_update_time_from_json(
            {}, "glue_jobs", "glue-job-1"
        )
        is None
    )


# JSON = sample data, but resource_type is not there
def test_get_last_update_time_no_resource_type(
    last_update_time_sample_data, metrics_storage
):
    assert (
        metrics_storage.get_resource_last_update_time_from_json(
            last_update_time_sample_data, "step_functions", "step-function-1"
        )
        is None
    )


# JSON = sample data, but resource_NAME is not there
def test_get_last_update_time_no_resource_name(
    last_update_time_sample_data, metrics_storage
):
    assert (
        metrics_storage.get_resource_last_update_time_from_json(
            last_update_time_sample_data, "glue_jobs", "nonexistent-job"
        )
        is None
    )


# JSON = sample data, return existing last_update_time
def test_get_last_update_time_valid_input(
    last_update_time_sample_data, metrics_storage
):
    expected_datetime = str_utc_datetime_to_datetime("2024-01-09 11:00:40.911000000")
    actual_datetime = metrics_storage.get_resource_last_update_time_from_json(
        last_update_time_sample_data, "glue_jobs", "glue-job-1"
    )
    assert actual_datetime == expected_datetime


@pytest.mark.parametrize(
    "scenario, last_update_times, resource_names, resource_type, expected_date",
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
            types.GLUE_DATA_QUALITY,
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
            types.GLUE_DATA_QUALITY,
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
            types.GLUE_DATA_QUALITY,
            # only one resource provided, so its last_update_time should be returned
            str_utc_datetime_to_datetime("2024-07-22 00:01:56.042000000"),
        ),
        (
            "scen4",
            [],
            ["test-de-ruleset-4"],
            types.GLUE_DATA_QUALITY,
            # no last_update_times found, so earliest writable time should be returned
            EARLIEST_WRITABLE_TIME,
        ),
    ],
)
def test_get_earliest_last_update_time_for_resource_set(
    scenario,
    last_update_times,
    resource_names,
    resource_type,
    expected_date,
    metrics_storage,
):
    with patch.object(
        TimestreamMetricsStorage,
        "get_earliest_writeable_time_for_resource_type",
        return_value=EARLIEST_WRITABLE_TIME,
    ):
        returned_min_date = (
            metrics_storage.get_earliest_last_update_time_for_resource_set(
                last_update_times, resource_names, resource_type
            )
        )
        assert (
            returned_min_date == expected_date
        ), f"Date mismatch for scenario {scenario}"

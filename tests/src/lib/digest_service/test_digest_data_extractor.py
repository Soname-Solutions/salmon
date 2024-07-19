from datetime import datetime
import re
from unittest.mock import patch
import pytest
from lib.core.constants import SettingConfigResourceTypes as types
from lib.digest_service import (
    DigestDataExtractorProvider,
    DigestException,
)

STAGE_NAME = "teststage"
EXPECTED_QUERY_COLUMNS = [
    "resource_type",
    "monitored_environment",
    "resource_name",
    "job_run_id",
    "execution",
    "failed",
    "succeeded",
    "execution_time_sec",
    "error_message",
]
START_TIME = datetime(2000, 1, 1, 0, 0, 0)
END_TIME = datetime(2000, 1, 2, 0, 0, 0)


@pytest.mark.parametrize(
    "scenario, resource_type",
    [
        ("scen1", types.GLUE_JOBS),
        ("scen2", types.GLUE_WORKFLOWS),
        ("scen3", types.LAMBDA_FUNCTIONS),
        ("scen4", types.STEP_FUNCTIONS),
        # Not yet implemented for Glue Crawlers and Data Catalogs
    ],
)
def test_digest_extractor_get_query(scenario, resource_type):
    timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    timestream_table_name = f"tstable-{resource_type}-metrics"

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        timestream_db_name=timestream_db_name,
        timestream_table_name=timestream_table_name,
    )

    returned_query = returned_extractor.get_query(START_TIME, END_TIME)
    returned_column_names = re.findall(r"\b(\w+)\b", returned_query)
    missing_columns = [
        column
        for column in EXPECTED_QUERY_COLUMNS
        if column not in returned_column_names
    ]
    assert missing_columns == [], f"Missing columns: {missing_columns}"


@pytest.mark.parametrize(
    "scenario, resource_type",
    [
        ("scen1", types.GLUE_JOBS),
        ("scen2", types.GLUE_WORKFLOWS),
        ("scen3", types.GLUE_DATA_CATALOGS),
        ("scen4", types.GLUE_CRAWLERS),
        ("scen5", types.LAMBDA_FUNCTIONS),
        ("scen6", types.STEP_FUNCTIONS),
    ],
)
@patch("lib.digest_service.digest_data_extractor.TimeStreamQueryRunner")
def test_digest_extract_runs_with_data(mock_query_runner, scenario, resource_type):
    timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    timestream_table_name = f"tstable-{resource_type}-metrics"
    query = "test_query"

    mock_runner_instance = mock_query_runner.return_value
    mock_runner_instance.is_table_empty.return_value = False
    mock_runner_instance.execute_query.return_value = {"data": "sample_data"}

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        timestream_db_name=timestream_db_name,
        timestream_table_name=timestream_table_name,
    )

    result = returned_extractor.extract_runs(query)

    mock_runner_instance.is_table_empty.assert_called_once_with(
        timestream_db_name, timestream_table_name
    )
    mock_runner_instance.execute_query.assert_called_once_with(query)
    assert result == {resource_type: {"data": "sample_data"}}


@pytest.mark.parametrize(
    "scenario, resource_type",
    [
        ("scen1", types.GLUE_JOBS),
        ("scen2", types.GLUE_WORKFLOWS),
        ("scen3", types.GLUE_DATA_CATALOGS),
        ("scen4", types.GLUE_CRAWLERS),
        ("scen5", types.LAMBDA_FUNCTIONS),
        ("scen6", types.STEP_FUNCTIONS),
        ("scen7", types.GLUE_DATA_QUALITY),
    ],
)
@patch("lib.digest_service.digest_data_extractor.TimeStreamQueryRunner")
def test_digest_extract_runs_no_data(mock_query_runner, scenario, resource_type):
    timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    timestream_table_name = f"tstable-{resource_type}-metrics"
    query = "test_query"

    mock_runner_instance = mock_query_runner.return_value
    mock_runner_instance.is_table_empty.return_value = True

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        timestream_db_name=timestream_db_name,
        timestream_table_name=timestream_table_name,
    )

    result = returned_extractor.extract_runs(query)

    mock_runner_instance.is_table_empty.assert_called_once_with(
        timestream_db_name, timestream_table_name
    )
    mock_runner_instance.execute_query.assert_not_called()
    assert result == {}


@pytest.mark.parametrize(
    "scenario, resource_type",
    [
        ("scen1", types.GLUE_JOBS),
        ("scen2", types.GLUE_WORKFLOWS),
        ("scen3", types.GLUE_DATA_CATALOGS),
        ("scen4", types.GLUE_CRAWLERS),
        ("scen5", types.LAMBDA_FUNCTIONS),
        ("scen6", types.STEP_FUNCTIONS),
        ("scen7", types.GLUE_DATA_QUALITY),
    ],
)
@patch("lib.digest_service.digest_data_extractor.TimeStreamQueryRunner")
def test_digest_extract_runs_exception(mock_query_runner, scenario, resource_type):
    timestream_db_name = f"timestream-salmon-metrics-events-storage-{STAGE_NAME}"
    timestream_table_name = f"tstable-{resource_type}-metrics"
    query = "test_query"

    mock_runner_instance = mock_query_runner.return_value
    mock_runner_instance.is_table_empty.side_effect = Exception("Can't connect to DB")

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        timestream_db_name=timestream_db_name,
        timestream_table_name=timestream_table_name,
    )

    with pytest.raises(DigestException):
        returned_extractor.extract_runs(query)

    mock_runner_instance.is_table_empty.assert_called_once_with(
        timestream_db_name, timestream_table_name
    )
    mock_runner_instance.execute_query.assert_not_called()

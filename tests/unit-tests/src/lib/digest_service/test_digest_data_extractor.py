from datetime import datetime
import re
from unittest.mock import MagicMock, patch
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
EXTRA_DQ_COLUMNS = ["context_type", "glue_table_name", "glue_db_name", "glue_job_name"]
EXPECTED_GLUE_CATALOGS_COLUMNS = [
    "resource_type",
    "monitored_environment",
    "resource_name",
    "tables_count",
    "tables_added",
    "partitions_count",
    "partitions_added",
    "indexes_count",
    "indexes_added",
]
START_TIME = datetime(2000, 1, 1, 0, 0, 0)
END_TIME = datetime(2000, 1, 2, 0, 0, 0)


@pytest.fixture
def mocked_metrics_storage():
    return MagicMock()


@pytest.mark.parametrize(
    "scenario, resource_type",
    [
        ("scen1", types.GLUE_JOBS),
        ("scen2", types.GLUE_WORKFLOWS),
        ("scen3", types.LAMBDA_FUNCTIONS),
        ("scen4", types.STEP_FUNCTIONS),
        ("scen5", types.GLUE_DATA_QUALITY),
        ("scen6", types.EMR_SERVERLESS),
        ("scen7", types.GLUE_CRAWLERS),
        ("scen8", types.GLUE_DATA_CATALOGS),
    ],
)
def test_digest_extractor_get_query(scenario, resource_type, mocked_metrics_storage):
    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        metrics_storage=mocked_metrics_storage,
    )

    returned_query = returned_extractor.get_query(START_TIME, END_TIME)
    returned_column_names = re.findall(r"\b(\w+)\b", returned_query)

    if resource_type == types.GLUE_DATA_CATALOGS:
        expected_columns = list(EXPECTED_GLUE_CATALOGS_COLUMNS)
    else:
        expected_columns = list(EXPECTED_QUERY_COLUMNS)
        if resource_type == types.GLUE_DATA_QUALITY:
            expected_columns += EXTRA_DQ_COLUMNS

    missing_columns = [
        column for column in expected_columns if column not in returned_column_names
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
        ("scen7", types.GLUE_DATA_QUALITY),
        ("scen8", types.EMR_SERVERLESS),
    ],
)
def test_digest_extract_runs_with_data(scenario, resource_type):
    query = "test_query"
    metrics_table_name = "sample_table_name"

    mocked_metrics_storage = MagicMock()
    mocked_metrics_storage.is_table_empty.return_value = False
    mocked_metrics_storage.execute_query.return_value = {"data": "sample_data"}

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        metrics_storage=mocked_metrics_storage,
    )
    returned_extractor.table_name = metrics_table_name

    result = returned_extractor.extract_runs(query)

    mocked_metrics_storage.is_table_empty.assert_called_once_with(metrics_table_name)
    mocked_metrics_storage.execute_query.assert_called_once_with(query)
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
        ("scen8", types.EMR_SERVERLESS),
    ],
)
def test_digest_extract_runs_no_data(scenario, resource_type):
    query = "test_query"
    metrics_table_name = "sample_table_name"

    mocked_metrics_storage = MagicMock()
    mocked_metrics_storage.is_table_empty.return_value = True

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        metrics_storage=mocked_metrics_storage,
    )
    returned_extractor.table_name = metrics_table_name

    result = returned_extractor.extract_runs(query)

    mocked_metrics_storage.is_table_empty.assert_called_once_with(metrics_table_name)
    mocked_metrics_storage.execute_query.assert_not_called()
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
        ("scen8", types.EMR_SERVERLESS),
    ],
)
def test_digest_extract_runs_exception(scenario, resource_type):
    query = "test_query"
    metrics_table_name = "sample_table_name"

    mocked_metrics_storage = MagicMock()
    mocked_metrics_storage.is_table_empty.side_effect = Exception("Can't connect to DB")

    returned_extractor = DigestDataExtractorProvider.get_digest_provider(
        resource_type=resource_type,
        metrics_storage=mocked_metrics_storage,
    )
    returned_extractor.table_name = metrics_table_name

    with pytest.raises(DigestException):
        returned_extractor.extract_runs(query)

    mocked_metrics_storage.is_table_empty.assert_called_once_with(metrics_table_name)
    mocked_metrics_storage.execute_query.assert_not_called()

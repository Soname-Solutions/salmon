from datetime import datetime
import pytest
from unittest.mock import patch, MagicMock
from lib.metrics_extractor import GlueDataQualityMetricExtractor
from lib.aws.glue_manager import (
    GlueManager,
    RulesetRun,
    RuleResult,
    RulesetDataSource,
    RulesetGlueTable,
)
from common import boto3_client_creator, get_measure_value, contains_required_items

RULESET_NAME = "test-ruleset-name"
TABLE_NAME = "test-glue-table-name"
DB_NAME = "test-glue-db-name"
JOB_NAME = "test-glue-job-name"

GLUE_MANAGER_CLASS_NAME = (
    "lib.metrics_extractor.glue_data_quality_metrics_extractor.GlueManager"
)
GET_EXECUTIONS_METHOD_NAME = f"{GLUE_MANAGER_CLASS_NAME}.get_data_quality_runs"

RULESET_RUN_GLUE_TABLE_SUCCESS = RulesetRun(
    ResultId="dqresult-218f5a67f3a23ab1046d6c6cb281641acef79737",
    Score=0.0,
    RulesetName=RULESET_NAME,
    RulesetEvaluationRunId="dqrun-e49928faa7174e8c40fd4573f4a90f0eea7896a7",
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 5, 0),
    RuleResults=[
        RuleResult(
            Name="Rule_1",
            Description='IsComplete "userId"',
            Result="PASS",
            EvaluatedMetrics={"Column.userId.Completeness": 1.0},
        )
    ],
    DataSource=RulesetDataSource(
        GlueTable=RulesetGlueTable(DatabaseName=DB_NAME, TableName=JOB_NAME)
    ),
)
RULESET_RUN_GLUE_JOB_SUCCESS = RulesetRun(
    ResultId="dqresult-620f35f4af4bf40c605fc989701e7a3008337701",
    Score=0.5,
    RulesetName=RULESET_NAME,
    EvaluationContext=RULESET_NAME,
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 5, 0),
    JobName=JOB_NAME,
    JobRunId="jr_eaed49a18cbe28d1b0f21e3cf949f6f2b2f5aa43019095547ef16f9294da9000",
    RuleResults=[
        RuleResult(
            Name="Rule_1",
            Description='IsComplete "userId"',
            Result="PASS",
            EvaluatedMetrics={"Column.userId.Completeness": 1.0},
        )
    ],
)

RULESET_RUN_GLUE_TABLE_ERROR = RulesetRun(
    ResultId="dqresult-218f5a67f3a23ab1046d6c6cb281641acef79737",
    Score=0.0,
    RulesetName=RULESET_NAME,
    RulesetEvaluationRunId="dqrun-e49928faa7174e8c40fd4573f4a90f0eea7896a7",
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 5, 0),
    RuleResults=[
        RuleResult(
            Name="Rule_1",
            Description="ColumnCount = 3",
            Result="FAIL",
            EvaluatedMetrics={"Dataset.*.ColumnCount": 9.0},
            EvaluationMessage="Dataset has 9.0 columns and failed to satisfy constraint",
        )
    ],
    DataSource=RulesetDataSource(
        GlueTable=RulesetGlueTable(DatabaseName=DB_NAME, TableName=JOB_NAME)
    ),
)

RULESET_RUN_GLUE_JOB_ERROR = RulesetRun(
    ResultId="dqresult-620f35f4af4bf40c605fc989701e7a3008337701",
    Score=0.5,
    RulesetName=RULESET_NAME,
    EvaluationContext=RULESET_NAME,
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 5, 0),
    JobName=JOB_NAME,
    JobRunId="jr_eaed49a18cbe28d1b0f21e3cf949f6f2b2f5aa43019095547ef16f9294da9000",
    RuleResults=[
        RuleResult(
            Name="Rule_1",
            Description="ColumnCount = 3",
            Result="FAIL",
            EvaluatedMetrics={"Dataset.*.ColumnCount": 12.0},
            EvaluationMessage="Dataset has 12.0 columns and failed to satisfy constraint",
        )
    ],
)

RULESET_RUN_MIXED_RULES = RulesetRun(
    ResultId="dqresult-218f5a67f3a23ab1046d6c6cb281641acef79737",
    Score=0.0,
    RulesetName=RULESET_NAME,
    RulesetEvaluationRunId="dqrun-e49928faa7174e8c40fd4573f4a90f0eea7896a7",
    StartedOn=datetime(2024, 1, 1, 0, 0, 0),
    CompletedOn=datetime(2024, 1, 1, 0, 5, 0),
    RuleResults=[
        RuleResult(
            Name="Rule_1",
            Description='IsComplete "userId"',
            Result="PASS",
            EvaluatedMetrics={"Column.userId.Completeness": 1.0},
        ),
        RuleResult(
            Name="Rule_2",
            Description="ColumnCount = 3",
            Result="FAIL",
            EvaluatedMetrics={"Dataset.*.ColumnCount": 9.0},
            EvaluationMessage="Dataset has 9.0 columns and failed to satisfy constraint",
        ),
        RuleResult(
            Name="Rule_3",
            Description="ColumnCount = 5",
            Result="FAIL",
            EvaluatedMetrics={"Dataset.*.ColumnCount": 9.0},
            EvaluationMessage="Dataset failed to satisfy constraint",
        ),
    ],
    DataSource=RulesetDataSource(
        GlueTable=RulesetGlueTable(DatabaseName=DB_NAME, TableName=JOB_NAME)
    ),
)


####################################################################
@pytest.fixture(scope="function", autouse=True)
def mock_glue_client():
    mock_glue_client = MagicMock()
    mock_glue_client.list_data_quality_results.return_value = {
        "Results": [{"ResultId": ""}]
    }
    mock_glue_client.batch_get_data_quality_result.return_value = {}
    with patch("boto3.client", return_value=mock_glue_client) as mock_glue:
        yield mock_glue


def test_two_completed_records_integrity(boto3_client_creator, mock_glue_client):
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [
            RULESET_RUN_GLUE_TABLE_SUCCESS,
            RULESET_RUN_GLUE_JOB_SUCCESS,
        ]

        extractor = GlueDataQualityMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=RULESET_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(
            since_time=since_time,
            result_ids=[
                RULESET_RUN_GLUE_TABLE_SUCCESS.ResultId,
                RULESET_RUN_GLUE_JOB_SUCCESS.ResultId,
            ],
        )

        required_dimensions = ["dq_result_id"]
        required_metrics = [
            "score",
            "context_type",
            "execution",
            "succeeded",
            "failed",
            "rules_succeeded",
            "rules_failed",
            "total_rules",
            "execution_time_sec",
            "error_message",
            "ruleset_run_id",
            "glue_table_name",
            "glue_db_name",
            "glue_job_name",
            "glue_job_run_id",
        ]

        mocked_get_executions.assert_called_once()  # mocked call executed as expected
        assert len(records) == 2, "There should be just two execution records"

        # check RULESET_RUN with GLUE_TABLE datasource
        assert contains_required_items(
            records[0], "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            records[0], "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"

        # check RULESET_RUN with GLUE_JOB datasource
        assert contains_required_items(
            records[1], "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            records[1], "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"


@pytest.mark.parametrize(
    "scenario, ruleset_run, succeeded, failed, rules_succeeded, rules_failed, total_rules, error_message",
    [
        (
            "scen1",
            RULESET_RUN_GLUE_TABLE_ERROR,
            "0",  # succeeded
            "1",  # failed
            "0",  # rules_succeeded
            "1",  # rules_failed
            "1",  # total_rules
            "Rule_1: Dataset has 9.0 columns and failed to satisfy constraint",
        ),
        (
            "scen2",
            RULESET_RUN_GLUE_JOB_ERROR,
            "0",  # succeeded
            "1",  # failed
            "0",  # rules_succeeded
            "1",  # rules_failed
            "1",  # total_rules
            "Rule_1: Dataset has 12.0 columns and failed to satisfy constraint",
        ),
        (
            "scen3",
            RULESET_RUN_MIXED_RULES,
            "0",  # succeeded
            "1",  # failed since not all rules passed
            "1",  # rules_succeeded
            "2",  # rules_failed
            "3",  # total_rules
            # error string concatenated and trimmed as expected
            "Rule_2: Dataset has 9.0 columns and failed to satisfy constraint; Rule_3: Dataset failed to satisfy ...",
        ),
    ],
)
def test_failed_dq_run(
    boto3_client_creator,
    scenario,
    ruleset_run,
    succeeded,
    failed,
    rules_succeeded,
    rules_failed,
    total_rules,
    error_message,
    mock_glue_client,
):
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [ruleset_run]

        extractor = GlueDataQualityMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=RULESET_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(
            since_time=since_time, result_ids=[ruleset_run.ResultId]
        )

        mocked_get_executions.assert_called_once()
        assert len(records) == 1, "There should be one execution record"
        assert get_measure_value(records[0], "succeeded") == succeeded
        assert get_measure_value(records[0], "failed") == failed
        assert get_measure_value(records[0], "rules_succeeded") == rules_succeeded
        assert get_measure_value(records[0], "rules_failed") == rules_failed
        assert get_measure_value(records[0], "total_rules") == total_rules
        assert get_measure_value(records[0], "error_message") == error_message


@pytest.mark.parametrize(
    "scenario, context_type, ruleset_run, succeeded, failed, rules_succeeded, rules_failed, total_rules",
    [
        (
            "scen1",
            GlueManager.DQ_Catalog_Context_Type,
            RULESET_RUN_GLUE_TABLE_SUCCESS,
            "1",  # succeeded
            "0",  # failed
            "1",  # rules_succeeded
            "0",  # rules_failed
            "1",  # total_rules
        ),
        (
            "scen2",
            GlueManager.DQ_Job_Context_Type,
            RULESET_RUN_GLUE_JOB_SUCCESS,
            "1",  # succeeded
            "0",  # failed
            "1",  # rules_succeeded
            "0",  # rules_failed
            "1",  # total_rules
        ),
    ],
)
def test_succeeded_dq_run(
    boto3_client_creator,
    scenario,
    context_type,
    ruleset_run,
    succeeded,
    failed,
    rules_succeeded,
    rules_failed,
    total_rules,
    mock_glue_client,
):
    with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
        mocked_get_executions.return_value = [ruleset_run]

        extractor = GlueDataQualityMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=RULESET_NAME,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, _ = extractor.prepare_metrics_data(
            since_time=since_time, result_ids=[ruleset_run.ResultId]
        )

        mocked_get_executions.assert_called_once()
        assert len(records) == 1, "There should be one execution record"
        assert get_measure_value(records[0], "context_type") == context_type
        assert get_measure_value(records[0], "succeeded") == succeeded
        assert get_measure_value(records[0], "failed") == failed
        assert get_measure_value(records[0], "rules_succeeded") == rules_succeeded
        assert get_measure_value(records[0], "rules_failed") == rules_failed
        assert get_measure_value(records[0], "total_rules") == total_rules
        assert get_measure_value(records[0], "error_message") == "None"


def test_no_dq_runs(
    boto3_client_creator,
):
    mock_glue_client = MagicMock()
    mock_glue_client.list_data_quality_results.return_value = {"Results": []}
    mock_glue_client.batch_get_data_quality_result.return_value = {}

    with patch(
        "boto3.client", return_value=mock_glue_client
    ) as mock_list_data_quality_results:
        with patch(GET_EXECUTIONS_METHOD_NAME) as mocked_get_executions:
            extractor = GlueDataQualityMetricExtractor(
                boto3_client_creator=boto3_client_creator,
                aws_client_name="glue",
                resource_name=RULESET_NAME,
                monitored_environment_name="env1",
                timestream_db_name="db_name1",
                timestream_metrics_table_name="table_name1",
            )

            since_time = datetime(2020, 1, 1, 0, 0, 0)
            records, _ = extractor.prepare_metrics_data(since_time=since_time)

            mocked_get_executions.assert_not_called()  # not called since no ResultIDs returned for the specified period
            assert len(records) == 0, "There shouldn't be execution records"

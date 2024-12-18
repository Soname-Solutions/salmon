import pytest
from lib.core.constants import SettingConfigResourceTypes as types, DigestSettings
from lib.digest_service import (
    DigestDataAggregator,
    DigestDataAggregatorProvider,
    AggregatedEntry,
    SummaryEntry,
)


@pytest.mark.parametrize(
    (
        "scenario, resource_name, resource_type, extracted_runs, resources_config, expected_status, "
        "expected_executions, expected_comments, insufficient_runs_alert"
    ),
    [
        (
            "scen1-no-runs-expected",
            "lambda-test",
            types.LAMBDA_FUNCTIONS,
            {},
            [
                {
                    "name": "lambda-test",
                    "region_name": "test-region",
                    "account_id": "123456789",
                    "minimum_number_of_runs": 0,
                }
            ],
            DigestSettings.STATUS_OK,
            0,
            "",
            False,
        ),
        (
            "scen2-one-run-expected",
            "glue-test",
            types.GLUE_JOBS,
            {},
            [
                {
                    "name": "glue-test",
                    "region_name": "test-region",
                    "account_id": "123456789",
                    "minimum_number_of_runs": 1,
                }
            ],
            DigestSettings.STATUS_ERROR,
            0,
            "Insufficient runs: 0 run(s) during the monitoring period (at least 1 expected).",
            True,
        ),
    ],
)
def test_get_aggregated_runs_empty_extracted_runs(
    scenario,
    resource_name,
    resource_type,
    extracted_runs,
    resources_config,
    expected_status,
    expected_executions,
    expected_comments,
    insufficient_runs_alert,
):
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)
    resource_agg_entry = result[resource_name]

    assert (
        resource_agg_entry.Status == expected_status
    ), f"Status mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Executions == expected_executions
    ), f"Executions mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.CommentsStr == expected_comments
    ), f"Comments mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.InsufficientRuns == insufficient_runs_alert
    ), f"Failures mismatch for scenario {scenario}"


def test_get_aggregated_runs_empty_resources_config():
    extracted_runs = {"step_functions": [{"resource_name": "step-function-test"}]}
    resources_config = []
    resource_type = types.STEP_FUNCTIONS
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)

    assert result == {}, "Expected empty dictionary when resources_config is empty"


@pytest.mark.parametrize(
    (
        "scenario, resource_name, resource_type, extracted_runs, resources_config, expected_status, "
        "expected_executions, expected_errors, expected_success_runs"
    ),
    [
        (
            "scen1-success-runs",
            "glue-workflow-test",
            types.GLUE_WORKFLOWS,
            {
                types.GLUE_WORKFLOWS: [
                    {
                        "resource_name": "glue-workflow-test",
                        "execution": "1",
                        "failed": "0",
                        "succeeded": "1",
                        "execution_time_sec": "12",
                    },
                    {
                        "resource_name": "glue-workflow-test",
                        "execution": "1",
                        "failed": "0",
                        "succeeded": "1",
                        "execution_time_sec": "13",
                    },
                ]
            },
            [
                {
                    "name": "glue-workflow-test",
                    "region_name": "test-region",
                    "account_id": "123456789",
                    "sla_seconds": 0,
                    "minimum_number_of_runs": 0,
                }
            ],
            DigestSettings.STATUS_OK,
            2,
            0,
            2,
        )
    ],
)
def test_get_aggregated_runs_with_success_runs(
    scenario,
    resource_name,
    resource_type,
    extracted_runs,
    resources_config,
    expected_status,
    expected_executions,
    expected_errors,
    expected_success_runs,
):
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)
    resource_agg_entry = result[resource_name]

    assert (
        resource_agg_entry.Status == expected_status
    ), f"Status mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Executions == expected_executions
    ), f"Executions mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Errors == expected_errors
    ), f"Errors mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Success == expected_success_runs
    ), f"Success runs mismatch for scenario {scenario}"


@pytest.mark.parametrize(
    (
        "scenario, resource_name, resource_type, extracted_runs, resources_config, expected_status, "
        "expected_executions, expected_errors, expected_success_runs"
    ),
    [
        (
            "scen1-failure-runs",
            "glue-crawler-test",
            types.GLUE_CRAWLERS,
            {
                types.GLUE_CRAWLERS: [
                    {
                        "resource_name": "glue-crawler-test",
                        "execution": "1",
                        "failed": "1",
                        "succeeded": "0",
                        "execution_time_sec": "12",
                        "job_run_id": "11111",
                        "error_message": "",
                    },
                    {
                        "resource_name": "glue-crawler-test",
                        "execution": "1",
                        "failed": "1",
                        "succeeded": "0",
                        "execution_time_sec": "2",
                        "job_run_id": "22222",
                        "error_message": "Failed",
                    },
                ]
            },
            [
                {
                    "name": "glue-crawler-test",
                    "sla_seconds": 0,
                    "minimum_number_of_runs": 0,
                    "region_name": "test_region",
                    "account_id": "test_account_id",
                }
            ],
            DigestSettings.STATUS_ERROR,
            2,
            2,
            0,
        ),
        (
            "scen2-mix-runs",
            "glue-job-test-2",
            types.GLUE_JOBS,
            {
                types.GLUE_JOBS: [
                    {
                        "resource_name": "glue-job-test-2",
                        "execution": "1",
                        "failed": "0",
                        "succeeded": "1",
                        "execution_time_sec": "3",
                    },
                    {
                        "resource_name": "glue-job-test-2",
                        "execution": "1",
                        "failed": "1",
                        "succeeded": "0",
                        "execution_time_sec": "1",
                        "job_run_id": "3333",
                        "error_message": "Failed",
                    },
                ]
            },
            [
                {
                    "name": "glue-job-test-2",
                    "sla_seconds": 0,
                    "minimum_number_of_runs": 0,
                    "region_name": "test_region",
                    "account_id": "test_account_id",
                }
            ],
            DigestSettings.STATUS_ERROR,
            2,
            1,
            1,
        ),
    ],
)
def test_get_aggregated_runs_with_errors(
    scenario,
    resource_name,
    resource_type,
    extracted_runs,
    resources_config,
    expected_status,
    expected_executions,
    expected_errors,
    expected_success_runs,
):
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)
    resource_agg_entry = result[resource_name]

    assert (
        resource_agg_entry.Status == expected_status
    ), f"Status mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Executions == expected_executions
    ), f"Executions mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Errors == expected_errors
    ), f"Errors mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Success == expected_success_runs
    ), f"Success runs mismatch for scenario {scenario}"
    assert (
        "Some runs have failed" in resource_agg_entry.CommentsStr
    ), f"Comments mismatch for scenario {scenario}"


@pytest.mark.parametrize(
    (
        "scenario, resource_name, resource_type,extracted_runs,  resources_config, expected_status, "
        "expected_executions, expected_errors, expected_success_runs, expected_warnings"
    ),
    [
        (
            "scen1-SLA-not-met-success",
            "glue-data-crawler-test",
            types.GLUE_CRAWLERS,
            {
                "resource_type1": [
                    {
                        "resource_name": "glue-data-crawler-test",
                        "execution": "1",
                        "failed": "0",
                        "succeeded": "1",
                        "execution_time_sec": "20",
                    },
                ]
            },
            [
                {
                    "name": "glue-data-crawler-test",
                    "region_name": "test-region",
                    "account_id": "123456789",
                    "sla_seconds": 10,
                    "minimum_number_of_runs": 0,
                }
            ],
            DigestSettings.STATUS_WARNING,
            1,
            0,
            1,
            1,
        ),
        (
            "scen2-SLA-not-met-error",
            "glue-data-crawler-test-2",
            types.GLUE_CRAWLERS,
            {
                "resource_type2": [
                    {
                        "resource_name": "glue-data-crawler-test-2",
                        "execution": "1",
                        "failed": "1",
                        "succeeded": "0",
                        "execution_time_sec": "15",
                        "job_run_id": "3333",
                        "error_message": "Failed",
                    },
                ]
            },
            [
                {
                    "name": "glue-data-crawler-test-2",
                    "sla_seconds": 10,
                    "minimum_number_of_runs": 0,
                    "region_name": "test_region",
                    "account_id": "test_account_id",
                }
            ],
            DigestSettings.STATUS_ERROR,
            1,
            1,
            0,
            1,
        ),
    ],
)
def test_get_aggregated_runs_with_warnings(
    scenario,
    resource_name,
    resource_type,
    extracted_runs,
    resources_config,
    expected_status,
    expected_executions,
    expected_errors,
    expected_success_runs,
    expected_warnings,
):
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)
    resource_agg_entry = result[resource_name]

    assert (
        resource_agg_entry.Status == expected_status
    ), f"Status mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Executions == expected_executions
    ), f"Executions mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Errors == expected_errors
    ), f"Errors mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Success == expected_success_runs
    ), f"Success runs mismatch for scenario {scenario}"
    assert (
        resource_agg_entry.Warnings == expected_warnings
    ), f"Warnings mismatch for scenario {scenario}"
    assert (
        "WARNING: Some runs haven't met SLA (=10 sec)."
        in resource_agg_entry.CommentsStr
    ), f"Comments mismatch for scenario {scenario}"


@pytest.mark.parametrize(
    ("scenario, resource_type, aggregated_runs"),
    [
        ("scen1-no-runs", types.GLUE_DATA_QUALITY, {}),
        (
            "scen2-no-runs",
            types.EMR_SERVERLESS,
            {
                "emr-test-2": AggregatedEntry(
                    Status=DigestSettings.STATUS_OK,
                    Executions=0,
                    Success=0,
                    Errors=0,
                    Warnings=0,
                    Comments=[],
                    InsufficientRuns=False,
                    HasSLABreach=False,
                    HasFailedAttempts=False,
                )
            },
        ),
    ],
)
def test_get_summary_entry_with_empty_data(scenario, resource_type, aggregated_runs):
    group_name = "emr-test-group"
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    returned_summary_entry = digest_aggregator.get_summary_entry(
        group_name, aggregated_runs
    )

    assert returned_summary_entry.ResourceType == resource_type
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.STATUS_OK
    assert returned_summary_entry.TotalExecutions == 0
    assert returned_summary_entry.TotalSuccess == 0
    assert returned_summary_entry.TotalFailures == 0
    assert returned_summary_entry.TotalWarnings == 0


@pytest.mark.parametrize(
    ("scenario, resource_type, aggregated_runs"),
    [
        (
            "scen1-success_runs",
            types.GLUE_CRAWLERS,
            {
                "glue-crawler-test": AggregatedEntry(
                    Status=DigestSettings.STATUS_OK,
                    Executions=5,
                    Success=5,
                    Errors=0,
                    Warnings=0,
                    Comments=[],
                    InsufficientRuns=False,
                    HasSLABreach=False,
                    HasFailedAttempts=False,
                )
            },
        ),
    ],
)
def test_get_summary_entry_with_success_runs(scenario, resource_type, aggregated_runs):
    group_name = "crawler-test-group"
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    returned_summary_entry = digest_aggregator.get_summary_entry(
        group_name, aggregated_runs
    )

    assert returned_summary_entry.ResourceType == resource_type
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.STATUS_OK
    assert returned_summary_entry.TotalExecutions == 5
    assert returned_summary_entry.TotalSuccess == 5
    assert returned_summary_entry.TotalFailures == 0
    assert returned_summary_entry.TotalWarnings == 0


@pytest.mark.parametrize(
    ("scenario, resource_type, aggregated_runs"),
    [
        (
            "scen1-errors",
            types.LAMBDA_FUNCTIONS,
            {
                "lambda-test-3": AggregatedEntry(
                    Status=DigestSettings.STATUS_ERROR,
                    Executions=3,
                    Success=1,
                    Errors=2,
                    Warnings=0,
                    Comments=[],
                    InsufficientRuns=True,
                    HasSLABreach=False,
                    HasFailedAttempts=False,
                )
            },
        ),
    ],
)
def test_get_summary_entry_with_errors(scenario, resource_type, aggregated_runs):
    group_name = "lambda-test-group"
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    returned_summary_entry = digest_aggregator.get_summary_entry(
        group_name, aggregated_runs
    )

    assert returned_summary_entry.ResourceType == resource_type
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.STATUS_ERROR
    assert returned_summary_entry.TotalExecutions == 3
    assert returned_summary_entry.TotalSuccess == 1
    assert returned_summary_entry.TotalFailures == 3
    assert returned_summary_entry.TotalWarnings == 0


@pytest.mark.parametrize(
    ("scenario, resource_type, aggregated_runs"),
    [
        (
            "scen1-warnings",
            types.GLUE_JOBS,
            {
                "glue-job-test-3": AggregatedEntry(
                    Status=DigestSettings.STATUS_WARNING,
                    Executions=3,
                    Success=3,
                    Errors=0,
                    Warnings=2,
                    Comments=[],
                    InsufficientRuns=False,
                    HasSLABreach=False,
                    HasFailedAttempts=False,
                )
            },
        ),
    ],
)
def test_get_summary_entry_with_warnings(scenario, resource_type, aggregated_runs):
    group_name = "glue-test-group"
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        resource_type
    )
    returned_summary_entry = digest_aggregator.get_summary_entry(
        group_name, aggregated_runs
    )

    assert returned_summary_entry.ResourceType == resource_type
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.STATUS_WARNING
    assert returned_summary_entry.TotalExecutions == 3
    assert returned_summary_entry.TotalSuccess == 3
    assert returned_summary_entry.TotalFailures == 0
    assert returned_summary_entry.TotalWarnings == 2

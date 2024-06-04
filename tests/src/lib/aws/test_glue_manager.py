import pytest
from unittest.mock import patch, MagicMock

from lib.aws.glue_manager import GlueManager, GlueManagerException


GLUE_WF_NAME = "TestWorkflow"
GLUE_WF_RUN_ID = "TestRunId"


@pytest.mark.parametrize(
    "scenario, workflow_graph, expected_result",
    [
        (
            "scen1 - one error",
            {
                "Run": {
                    "Graph": {
                        "Nodes": [
                            {
                                "Type": "JOB",
                                "Job": {
                                    "Name": "TestJob",
                                    "ErrorMessage": "Test job error",
                                },
                            }
                        ]
                    }
                }
            },
            "JOB Error: Test job error",
        ),
        (
            "scen2 - two errors",
            {
                "Run": {
                    "Graph": {
                        "Nodes": [
                            {
                                "Type": "JOB",
                                "Job": {
                                    "Name": "TestJob",
                                    "ErrorMessage": "Test job error",
                                },
                            },
                            {
                                "Type": "TRIGGER",
                                "Job": {
                                    "Name": "TestTrigger",
                                    "ErrorMessage": "Test trigger error",
                                },
                            },
                        ]
                    }
                }
            },
            "Total Errors: 2. JOB Error: Test job error; TRIGGER Error: Test trigger error",
        ),
        (
            "scen3 - no errors",
            {"Run": {"Graph": {"Nodes": []}}},
            None,
        ),
        (
            "scen4 - no errors",
            {
                "Run": {
                    "Graph": {"Nodes": [{"Type": "JOB", "Job": {"Name": "TestJob"}}]}
                }
            },
            None,
        ),
        (
            "scen5 - long error message",
            {
                "Run": {
                    "Graph": {
                        "Nodes": [
                            {
                                "Type": "CRAWLER",
                                "Job": {
                                    "Name": "TestJob",
                                    "ErrorMessage": "Test job error_" + "x" * 50,
                                },
                            }
                        ]
                    }
                }
            },
            "CRAWLER Error: Test job error_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx...",
        ),
    ],
)
@patch("boto3.client")
def test_generate_workflow_run_error_message(
    mock_boto_client, scenario, workflow_graph, expected_result
):
    mock_glue_client = MagicMock()
    mock_boto_client.return_value = mock_glue_client
    mock_glue_client.get_workflow_run.return_value = workflow_graph

    glue_manager = GlueManager()
    result = glue_manager.generate_workflow_run_error_message(
        GLUE_WF_NAME, GLUE_WF_RUN_ID
    )

    mock_glue_client.get_workflow_run.assert_called_once()
    mock_glue_client.get_workflow_run.assert_called_with(
        Name=GLUE_WF_NAME,
        RunId=GLUE_WF_RUN_ID,
        IncludeGraph=True,
    )
    assert result == expected_result, f"Mismatch for scenario {scenario}"


@patch("boto3.client")
def test_generate_workflow_run_error_message_exception(mock_boto_client):
    mock_glue_client = MagicMock()
    mock_boto_client.return_value = mock_glue_client

    error_message = "Can't get workflow run graph"
    mock_glue_client.get_workflow_run.side_effect = Exception(error_message)

    with pytest.raises(
        GlueManagerException,
        match=f"Error getting glue workflow error message: {error_message}",
    ):
        glue_manager = GlueManager()
        glue_manager.generate_workflow_run_error_message(GLUE_WF_NAME, GLUE_WF_RUN_ID)

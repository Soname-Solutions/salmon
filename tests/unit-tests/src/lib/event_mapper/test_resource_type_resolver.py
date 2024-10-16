import pytest

from lib.core.constants import SettingConfigResourceTypes as types
from lib.event_mapper.resource_type_resolver import ResourceTypeResolver


@pytest.mark.parametrize(
    "scenario, event, expected_resource_type",
    [
        (
            "scen1",
            {"source": "aws.glue", "detail-type": "Glue Job State Change"},
            types.GLUE_JOBS,
        ),
        (
            "scen2",
            {
                "source": "salmon.glue_workflow",
                "detail-type": "Glue Workflow State Change",
            },
            types.GLUE_WORKFLOWS,
        ),
        (
            "scen3",
            {
                "source": "aws.glue",
                "detail-type": "Glue Data Catalog Database State Change",
            },
            types.GLUE_DATA_CATALOGS,
        ),
        (
            "scen4",
            {"source": "aws.glue", "detail-type": "Glue Crawler State Change"},
            types.GLUE_CRAWLERS,
        ),
        (
            "scen5",
            {
                "source": "salmon.lambda",
                "detail-type": "Lambda Function Execution State Change",
            },
            types.LAMBDA_FUNCTIONS,
        ),
        (
            "scen6",
            {
                "source": "aws.states",
                "detail-type": "Step Functions Execution Status Change",
            },
            types.STEP_FUNCTIONS,
        ),
    ],
)
def test_resource_type_resolve(scenario, event, expected_resource_type):
    assert (
        ResourceTypeResolver.resolve(event) == expected_resource_type
    ), f"Mismatch for scenario {scenario}"


@pytest.mark.parametrize(
    "scenario, event",
    [
        (
            "scen1",
            {
                "source": "invalid-source",
                "detail-type": "invalid-detail-type",
            },
        ),
        (
            "scen2",
            {
                "detail-type": "invalid-detail-type",
            },
        ),
        (
            "scen3",
            {
                "source": "invalid-source",
            },
        ),
        (
            "scen4",
            {
                "source": "aws.glue",
                "detail-type": "invalid-detail-type",
            },
        ),
    ],
)
def test_resolve_keyerror(scenario, event):
    with pytest.raises(KeyError):
        ResourceTypeResolver.resolve(event), f"Mismatch for scenario {scenario}"

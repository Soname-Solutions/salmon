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
        (
            "scen7",
            {
                "source": "aws.glue",
                "detail-type": "Glue Data Catalog Table State Change",
            },
            types.GLUE_DATA_CATALOGS,
        ),
        (
            "scen8",
            {
                "source": "aws.emr-serverless",
                "detail-type": "EMR Serverless Job Run State Change",
            },
            types.EMR_SERVERLESS,
        ),
        (
            "scen9",
            {
                "source": "aws.glue-dataquality",
                "detail-type": "Data Quality Evaluation Results Available",
            },
            types.GLUE_DATA_QUALITY,
        ),
        (
            "scen10",
            {
                "source": "aws.emr-serverless",
                "detail-type": "EMR Serverless Job Resource Utilization Update",
            },
            None,
        ),
        (
            "scen11",
            {
                "source": "aws.glue",
                "detail-type": "Glue Job Run Status",
            },
            None,
        ),
    ],
)
def test_resource_type_resolve(scenario, event, expected_resource_type):
    assert (
        ResourceTypeResolver.resolve(event) == expected_resource_type
    ), f"Mismatch for scenario {scenario}"

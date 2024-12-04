from datetime import datetime

from unittest.mock import patch
from lib.metrics_extractor import GlueCatalogsMetricExtractor
from lib.aws.glue_manager import CatalogData, TableModel

from common import boto3_client_creator, get_measure_value, contains_required_items

DATA_CATALOG_DB = "test-db"
CATALOG_ID = "123456789"

CATALOG_DATA = CatalogData(
    DatabaseName=DATA_CATALOG_DB,
    TableList=[
        TableModel(
            Name="test_table1",
            CatalogId=CATALOG_ID,
            CreateTime=datetime(2024, 10, 1, 12, 0, 0),
            UpdateTime=datetime(2024, 10, 1, 12, 3, 0),
            PartitionsCount=2,
            IndexesCount=1,
        ),
        TableModel(
            Name="test_table2",
            CatalogId=CATALOG_ID,
            CreateTime=datetime(2024, 10, 2, 12, 0, 0),
            UpdateTime=datetime(2024, 10, 2, 12, 3, 0),
            PartitionsCount=4,
            IndexesCount=5,
        ),
        TableModel(
            Name="test_table3",
            CatalogId=CATALOG_ID,
            CreateTime=datetime(2024, 10, 3, 12, 0, 0),
            UpdateTime=datetime(2024, 10, 3, 12, 3, 0),
            PartitionsCount=7,
            IndexesCount=0,
        ),
    ],
)


####################################################################
def test_data_catalog_metrics_extractor(boto3_client_creator):
    with patch(
        "lib.metrics_extractor.glue_catalogs_metrics_extractor.GlueManager.get_catalog_data"
    ) as mocked_get_catalog:
        mocked_get_catalog.return_value = CATALOG_DATA

        extractor = GlueCatalogsMetricExtractor(
            boto3_client_creator=boto3_client_creator,
            aws_client_name="glue",
            resource_name=DATA_CATALOG_DB,
            monitored_environment_name="env1",
            timestream_db_name="db_name1",
            timestream_metrics_table_name="table_name1",
        )

        since_time = datetime(2020, 1, 1, 0, 0, 0)
        records, common_attributes = extractor.prepare_metrics_data(
            since_time=since_time
        )

        required_dimensions = ["catalog_id"]
        required_metrics = [
            "tables_count",
            "partitions_count",
            "indexes_count",
        ]

        record_in_scope = records[0]
        print("RECORD ", record_in_scope)

        mocked_get_catalog.assert_called_once()  # mocked call executed as expected
        assert len(records) == 1, "There should be only one glue catalog record"
        assert contains_required_items(
            record_in_scope, "Dimensions", required_dimensions
        ), "Not all required dimensions for timestream record are present"
        assert contains_required_items(
            record_in_scope, "MeasureValues", required_metrics
        ), "Not all required metrics for timestream record are present"

        assert CATALOG_DATA.CatalogID == CATALOG_ID
        assert CATALOG_DATA.TotalTableCount == 3
        assert CATALOG_DATA.TotalPartitionsCount == 13
        assert CATALOG_DATA.TotalIndexesCount == 6

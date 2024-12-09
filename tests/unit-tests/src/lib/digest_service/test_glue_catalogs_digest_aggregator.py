from lib.core.constants import SettingConfigResourceTypes as types, DigestSettings
from lib.digest_service import (
    GlueCatalogAggregatedEntry,
    GlueCatalogSummaryEntry,
    DigestDataAggregatorProvider,
)

RESOURCE_TYPE = types.GLUE_DATA_CATALOGS
TEST_RESOURCE_NAME = "test-glue-db"


def test_get_aggregated_runs_empty_extracted_runs():
    extracted_runs = {}
    resources_config = [{"name": TEST_RESOURCE_NAME}]
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)
    resource_agg_entry: GlueCatalogAggregatedEntry = result[TEST_RESOURCE_NAME]
    assert resource_agg_entry.Status == DigestSettings.NO_STATUS
    assert resource_agg_entry.Tables == 0
    assert resource_agg_entry.Partitions == 0
    assert resource_agg_entry.Indexes == 0
    assert resource_agg_entry.TablesAdded == 0
    assert resource_agg_entry.PartitionsAdded == 0
    assert resource_agg_entry.IndexesAdded == 0


def test_get_aggregated_runs_empty_resources_config():
    resources_config = {}
    extracted_runs = {RESOURCE_TYPE: [{"resource_name": TEST_RESOURCE_NAME}]}
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    result = digest_aggregator.get_aggregated_runs(extracted_runs, resources_config)

    assert result == {}, "Expected empty dictionary when resources_config is empty"


def test_get_aggregated_glue_catalogs_runs():
    extracted_data = {
        RESOURCE_TYPE: [
            {
                "resource_name": TEST_RESOURCE_NAME,
                "tables_count": "14",
                "tables_added": "1",
                "partitions_count": "1",
                "partitions_added": "0",
                "indexes_count": "2",
                "indexes_added": "0",
            }
        ]
    }
    resources_config = [{"name": TEST_RESOURCE_NAME}]
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    result = digest_aggregator.get_aggregated_runs(extracted_data, resources_config)

    resource_agg_entry: GlueCatalogAggregatedEntry = result[TEST_RESOURCE_NAME]
    assert resource_agg_entry.Status == DigestSettings.NO_STATUS
    assert resource_agg_entry.Tables == 14
    assert resource_agg_entry.TablesAdded == 1
    assert resource_agg_entry.Partitions == 1
    assert resource_agg_entry.PartitionsAdded == 0
    assert resource_agg_entry.Indexes == 2
    assert resource_agg_entry.IndexesAdded == 0


def test_get_aggregated_glue_catalogs_runs_with_warnings():
    extracted_data = {
        RESOURCE_TYPE: [
            {
                "resource_name": TEST_RESOURCE_NAME,
                "tables_count": "5",
                "tables_added": "-1",
                "partitions_count": "1",
                "partitions_added": "4",
                "indexes_count": "2",
                "indexes_added": "0",
            }
        ]
    }
    resources_config = [{"name": TEST_RESOURCE_NAME}]
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    result = digest_aggregator.get_aggregated_runs(extracted_data, resources_config)

    resource_agg_entry: GlueCatalogAggregatedEntry = result[TEST_RESOURCE_NAME]
    assert resource_agg_entry.Status == DigestSettings.STATUS_WARNING
    assert resource_agg_entry.Tables == 5
    assert resource_agg_entry.TablesAdded == -1
    assert resource_agg_entry.Partitions == 1
    assert resource_agg_entry.PartitionsAdded == 4
    assert resource_agg_entry.Indexes == 2
    assert resource_agg_entry.IndexesAdded == 0
    assert (
        resource_agg_entry.CommentsStr
        == "WARNING: Some Glue Data Catalog objects deleted."
    )


def test_get_summary_entry_with_empty_data():
    group_name = "glue-test-group"
    aggregated_runs = {}
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    returned_summary_entry: GlueCatalogSummaryEntry = (
        digest_aggregator.get_summary_entry(group_name, aggregated_runs)
    )

    assert returned_summary_entry.ResourceType == RESOURCE_TYPE
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.NO_STATUS
    assert returned_summary_entry.TotalTables == 0
    assert returned_summary_entry.TotalTablesAdded == 0
    assert returned_summary_entry.TotalPartitions == 0
    assert returned_summary_entry.TotalPartitionsAdded == 0
    assert returned_summary_entry.TotalIndexes == 0
    assert returned_summary_entry.TotalIndexesAdded == 0


def test_get_glue_catalogs_summary_entry():
    aggregated_runs = {
        TEST_RESOURCE_NAME: GlueCatalogAggregatedEntry(
            Tables=4,
            Partitions=3,
            Indexes=2,
            TablesAdded=0,
            PartitionsAdded=1,
            IndexesAdded=-1,
        )
    }
    group_name = "glue-test-group"
    digest_aggregator = DigestDataAggregatorProvider.get_aggregator_provider(
        RESOURCE_TYPE
    )
    returned_summary_entry: GlueCatalogSummaryEntry = (
        digest_aggregator.get_summary_entry(group_name, aggregated_runs)
    )

    assert returned_summary_entry.ResourceType == RESOURCE_TYPE
    assert returned_summary_entry.MonitoringGroup == group_name
    assert returned_summary_entry.Status == DigestSettings.STATUS_WARNING
    assert returned_summary_entry.TotalTables == 4
    assert returned_summary_entry.TotalTablesAdded == 0
    assert returned_summary_entry.TotalPartitions == 3
    assert returned_summary_entry.TotalPartitionsAdded == 1
    assert returned_summary_entry.TotalIndexes == 2
    assert returned_summary_entry.TotalIndexesAdded == -1

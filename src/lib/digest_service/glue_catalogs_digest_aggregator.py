from pydantic import BaseModel
from typing import Dict, DefaultDict
from collections import defaultdict

from lib.core.constants import DigestSettings, SettingConfigs
from lib.digest_service import DigestDataAggregator, ResourceConfig


class GlueCatalogRun(BaseModel):
    tables_added: int = 0
    partitions_added: int = 0
    indexes_added: int = 0
    tables_count: int = 0
    partitions_count: int = 0
    indexes_count: int = 0


class GlueCatalogAggregatedEntry(BaseModel):
    Tables: int = 0
    Partitions: int = 0
    Indexes: int = 0
    TablesAdded: int = 0
    PartitionsAdded: int = 0
    IndexesAdded: int = 0

    @property
    def Status(self) -> str:
        if self.TablesAdded < 0 or self.PartitionsAdded < 0 or self.IndexesAdded < 0:
            return DigestSettings.STATUS_WARNING
        return DigestSettings.NO_STATUS

    @property
    def CommentsStr(self) -> str:
        """Returns the comments as a single string separated by newlines."""
        return "<br/>".join(self.generate_comments())

    def generate_comments(self) -> list:
        """Generates a list of comments based on conditions."""
        conditions_and_messages = [
            (
                self.TablesAdded < 0,
                "WARNING: Some Glue Data Catalog Tables have been deleted.",
            ),
            (
                self.PartitionsAdded < 0,
                "WARNING: Some Glue Data Catalog Partitions have been deleted.",
            ),
            (
                self.IndexesAdded < 0,
                "WARNING: Some Glue Data Catalog Indexes have been deleted.",
            ),
        ]

        return [message for condition, message in conditions_and_messages if condition]


class GlueCatalogSummaryEntry(BaseModel):
    ResourceType: str
    MonitoringGroup: str
    EntryList: list[GlueCatalogAggregatedEntry]

    @property
    def TotalTables(self) -> int:
        return sum(table.Tables for table in self.EntryList)

    @property
    def TotalPartitions(self) -> int:
        return sum(table.Partitions for table in self.EntryList)

    @property
    def TotalIndexes(self) -> int:
        return sum(table.Indexes for table in self.EntryList)

    @property
    def TotalTablesAdded(self) -> int:
        return sum(table.TablesAdded for table in self.EntryList)

    @property
    def TotalPartitionsAdded(self) -> int:
        return sum(table.PartitionsAdded for table in self.EntryList)

    @property
    def TotalIndexesAdded(self) -> int:
        return sum(table.IndexesAdded for table in self.EntryList)

    @property
    def Status(self) -> str:
        if (
            self.TotalTablesAdded < 0
            or self.TotalPartitionsAdded < 0
            or self.TotalIndexesAdded < 0
        ):
            return DigestSettings.STATUS_WARNING
        return DigestSettings.NO_STATUS

    @property
    def ServiceName(self) -> str:
        return SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES.get(self.ResourceType)


class GlueCatalogsDigestAggregator(DigestDataAggregator):
    """
    Aggregates metrics specific to Glue Data Catalog resources.
    """

    def __init__(self, resource_type: str):
        self.resource_type = resource_type
        self.aggregated_runs: DefaultDict[
            str, GlueCatalogAggregatedEntry
        ] = defaultdict(GlueCatalogAggregatedEntry)

    def _get_runs_by_resource_name(
        self, data: dict, resource_name: str
    ) -> list[GlueCatalogRun]:
        """Gets runs related to specific resource name."""
        return [
            GlueCatalogRun(**entry)
            for entries in data.values()
            for entry in entries
            if entry["resource_name"] == resource_name
        ]

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: list
    ) -> Dict[str, GlueCatalogAggregatedEntry]:
        """Aggregates data for each resource specified in the configurations."""

        configs = [ResourceConfig(**item) for item in resources_config]
        for resource_config in configs:
            resource_runs = self._get_runs_by_resource_name(
                data=extracted_runs, resource_name=resource_config.name
            )
            agg_entry = self.aggregated_runs[resource_config.name]

            for run in resource_runs:
                agg_entry.Tables += run.tables_count
                agg_entry.Partitions += run.partitions_count
                agg_entry.Indexes += run.indexes_count
                agg_entry.TablesAdded += run.tables_added
                agg_entry.PartitionsAdded += run.partitions_added
                agg_entry.IndexesAdded += run.indexes_added

        return dict(self.aggregated_runs)

    def get_summary_entry(
        self, group_name: str, aggregated_runs: Dict[str, GlueCatalogAggregatedEntry]
    ) -> GlueCatalogSummaryEntry:
        """Calculates and returns summary entry for aggregated_runs."""

        return GlueCatalogSummaryEntry(
            ResourceType=self.resource_type,
            MonitoringGroup=group_name,
            EntryList=list(aggregated_runs.values()),
        )

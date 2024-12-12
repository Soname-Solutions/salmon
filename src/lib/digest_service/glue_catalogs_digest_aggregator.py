from pydantic import BaseModel
from typing import Dict, DefaultDict
from collections import defaultdict

from lib.core.constants import DigestSettings, SettingConfigs
from lib.digest_service import DigestDataAggregator


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
        if self.Status == DigestSettings.STATUS_WARNING:
            return "WARNING: Some Glue Data Catalog object(s) deleted."
        return ""


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

    def get_aggregated_runs(
        self, extracted_runs: dict, resources_config: list
    ) -> Dict[str, GlueCatalogAggregatedEntry]:
        """Aggregates data for each resource specified in the configurations."""

        for resource_config in resources_config:
            resource_name = resource_config["name"]
            resource_runs = self._get_runs_by_resource_name(
                data=extracted_runs, resource_name=resource_name
            )
            entry = self.aggregated_runs[resource_name]

            for run in resource_runs:
                entry.TablesAdded += int(run.get("tables_added", 0))
                entry.PartitionsAdded += int(run.get("partitions_added", 0))
                entry.IndexesAdded += int(run.get("indexes_added", 0))
                entry.Tables += int(run.get("tables_count", 0))
                entry.Partitions += int(run.get("partitions_count", 0))
                entry.Indexes += int(run.get("indexes_count", 0))

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

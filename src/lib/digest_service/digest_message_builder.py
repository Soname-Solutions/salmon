from datetime import datetime
from typing import Dict, List

from lib.core.constants import SettingConfigs, SettingConfigResourceTypes as types
from lib.digest_service import (
    AggregatedEntry,
    SummaryEntry,
    GlueCatalogAggregatedEntry,
    GlueCatalogSummaryEntry,
)


class DigestMessageBuilder:
    """
    Class which provides unified functionality for constructing the message body of the digest report.
    """

    SUMMARY_TABLE_HEADERS = [
        "Monitoring Group",
        "Service",
        "Executions",
        "Success",
        "Failures",
        "Warnings",
    ]
    BODY_TABLE_HEADERS = ["Resource Name", "Success", "Errors", "Warnings", "Comments"]
    HEADER_STYLE = "header"
    TEXT_STYLE = "h11"

    # specific to Glue Data Catalogs
    GLUE_CATALOG_SUMMARY_TABLE_HEADERS = [
        "Monitoring Group",
        "Service",
        "Total Tables",
        "Total Partitions",
        "Total Indexes",
        "Delta Tables",
        "Delta Partitions",
        "Delta Indexes",
    ]
    GLUE_CATALOG_BODY_TABLE_HEADERS = [
        "Resource Name",
        "Tables",
        "Partitions",
        "Indexes",
        "Delta Tables",
        "Delta Partitions",
        "Delta Indexes",
    ]

    def __init__(self, digest_data: dict):
        self.digest_data = digest_data
        self.message_body: List[dict] = []

    def _create_table(self, header_values: List[str], rows: List[dict]) -> dict:
        return {
            "table": {
                "header": {"values": header_values},
                "rows": rows,
            }
        }

    def _create_table_row(self, values: list, style: str = None) -> dict:
        row = {"values": values}
        if style:
            row["style"] = style
        return row

    def _create_text_part(self, text: str, style: str) -> dict:
        return {"text": text, "style": style}

    def _create_glue_catalog_table(
        self, runs_data: Dict[str, GlueCatalogAggregatedEntry]
    ) -> dict:
        """Creates a table specific to Glue Data Catalog resources."""
        rows = [
            self._create_table_row(
                values=[
                    resource_name,
                    entry.Tables,
                    entry.Partitions,
                    entry.Indexes,
                    entry.DeltaTables,
                    entry.DeltaPartitions,
                    entry.DeltaIndexes,
                ],
                style=entry.Status,
            )
            for resource_name, entry in runs_data.items()
        ]
        return self._create_table(
            header_values=self.GLUE_CATALOG_BODY_TABLE_HEADERS, rows=rows
        )

    def _create_generic_resource_table(
        self, runs_data: Dict[str, AggregatedEntry]
    ) -> dict:
        """Creates a table for resource types other than Glue Data Catalogs."""
        rows = [
            self._create_table_row(
                values=[
                    resource_name,
                    entry.Success,
                    entry.Errors,
                    entry.Warnings,
                    entry.CommentsStr,
                ],
                style=entry.Status,
            )
            for resource_name, entry in runs_data.items()
        ]
        return self._create_table(header_values=self.BODY_TABLE_HEADERS, rows=rows)

    def _create_glue_catalog_summary_table(
        self, summary_data: list[GlueCatalogSummaryEntry]
    ) -> None:
        """Generates a summary table for Glue Data Catalog resources."""
        rows = []
        for summary_entry in summary_data:
            rows.append(
                self._create_table_row(
                    values=[
                        summary_entry.MonitoringGroup,
                        summary_entry.ServiceName,
                        summary_entry.TotalTables,
                        summary_entry.TotalPartitions,
                        summary_entry.TotalIndexes,
                        summary_entry.TotalDeltaTables,
                        summary_entry.TotalDeltaPartitions,
                        summary_entry.TotalDeltaIndexes,
                    ],
                    style=summary_entry.Status,
                )
            )
        return self._create_table(
            header_values=self.GLUE_CATALOG_SUMMARY_TABLE_HEADERS, rows=rows
        )

    def _create_generic_summary_table(self, summary_data: list[SummaryEntry]) -> None:
        """Generates a summary table for resource types (excluding Glue Data Catalogs)."""
        rows = []
        for summary_entry in summary_data:
            rows.append(
                self._create_table_row(
                    values=[
                        summary_entry.MonitoringGroup,
                        summary_entry.ServiceName,
                        summary_entry.TotalExecutions,
                        summary_entry.TotalSuccess,
                        summary_entry.TotalFailures,
                        summary_entry.TotalWarnings,
                    ],
                    style=summary_entry.Status,
                )
            )

        return self._create_table(header_values=self.SUMMARY_TABLE_HEADERS, rows=rows)

    def _categorize_summary_data(self) -> tuple[list, list]:
        """Categorizes summary data into Glue Data Catalogs-specific and generic groups."""
        glue_summary_data = []
        generic_summary_data = []

        for item in self.digest_data:
            for _, group_data in item.items():
                for resource_type, resource_data in group_data.items():
                    summary_entry = resource_data.get("summary", {})
                    if resource_type == types.GLUE_DATA_CATALOGS:
                        glue_summary_data.append(summary_entry)
                    else:
                        generic_summary_data.append(summary_entry)

        return glue_summary_data, generic_summary_data

    def _append_resource_tables(self) -> None:
        """Appends resource-specific tables for all monitoring groups to the message body."""

        for item in self.digest_data:
            for monitoring_group, group_data in item.items():
                for resource_type, resource_data in group_data.items():
                    runs_data = resource_data.get("runs", {})
                    service_name = SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES.get(
                        resource_type
                    )

                    resource_report_header = self._create_text_part(
                        text=f"{monitoring_group}: {service_name}",
                        style=self.HEADER_STYLE,
                    )
                    self.message_body.append(resource_report_header)

                    if resource_type == types.GLUE_DATA_CATALOGS:
                        table = self._create_glue_catalog_table(runs_data)
                    else:
                        table = self._create_generic_resource_table(runs_data)
                    self.message_body.append(table)

    def _append_summary_tables(self) -> None:
        """
        Appends summary tables to the message body.
        Separate logic is applied for Glue Data Catalog resources compared to other resource types.
        """
        glue_summary_data, generic_summary_data = self._categorize_summary_data()

        if glue_summary_data:
            self.message_body.append(
                self._create_glue_catalog_summary_table(summary_data=glue_summary_data)
            )

        if generic_summary_data:
            self.message_body.append(
                self._create_generic_summary_table(
                    summary_data=generic_summary_data,
                )
            )

    def generate_message_body(
        self, digest_start_time: datetime, digest_end_time: datetime
    ) -> list:
        """Generates message body for the digest report."""
        self.message_body.append(
            self._create_text_part(text="Digest Summary", style=self.HEADER_STYLE)
        )
        self.message_body.append(
            self._create_text_part(
                text=(
                    f"This report has been generated for the period "
                    f"from {digest_start_time.strftime('%B %d, %Y %I:%M %p')} "
                    f"to {digest_end_time.strftime('%B %d, %Y %I:%M %p')}."
                ),
                style=self.TEXT_STYLE,
            )
        )
        self._append_summary_tables()
        self._append_resource_tables()

        return self.message_body

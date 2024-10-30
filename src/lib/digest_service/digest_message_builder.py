from datetime import datetime
from typing import Dict, List
from lib.core.constants import SettingConfigs
from lib.digest_service import AggregatedEntry, SummaryEntry


class DigestMessageBuilder:
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

    def _get_summary_table(self) -> dict:
        """Generates a summary table in the digest message."""
        rows = []

        for item in self.digest_data:
            for group_name, group_data in item.items():
                for resource_type, resource_data in group_data.items():
                    service_name = SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES[
                        resource_type
                    ]
                    summary: SummaryEntry = resource_data["summary"]

                    row = self._create_table_row(
                        values=[
                            group_name,
                            service_name,
                            summary.Executions,
                            summary.Success,
                            summary.Failures,
                            summary.Warnings,
                        ],
                        style=summary.Status,
                    )
                    rows.append(row)

        return self._create_table(header_values=self.SUMMARY_TABLE_HEADERS, rows=rows)

    def _get_resource_table(self, runs_data: Dict[str, AggregatedEntry]) -> dict:
        """Generates a digest table for specific monitoring group and resource type."""
        rows = [
            self._create_table_row(
                values=[
                    resource_name,
                    entry.Success,
                    entry.Errors,
                    entry.Warnings,
                    "<br/>".join(entry.Comments),
                ],
                style=entry.Status,
            )
            for resource_name, entry in runs_data.items()
        ]
        return self._create_table(header_values=self.BODY_TABLE_HEADERS, rows=rows)

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

        # summary table
        summary_table = self._get_summary_table()
        self.message_body.append(summary_table)

        # monitoriting-group-resource-type-level tables
        for item in self.digest_data:
            for monitoring_group in item:
                for resource_type in item[monitoring_group]:
                    runs_data = item[monitoring_group][resource_type]["runs"]

                    service_name = SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES[
                        resource_type
                    ]
                    resource_report_header = self._create_text_part(
                        text=f"{monitoring_group}: {service_name}",
                        style=self.HEADER_STYLE,
                    )
                    self.message_body.append(resource_report_header)
                    resource_table = self._get_resource_table(runs_data)
                    self.message_body.append(resource_table)

        return self.message_body

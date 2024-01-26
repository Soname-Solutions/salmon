from datetime import datetime


class DigestMessageBuilder:
    def __init__(self, digest_data: dict):
        self.digest_data = digest_data
        self.message_body = []

    def _get_summary_table(self) -> dict:
        """Generates a summary table in the digest message."""
        return {
            "table": {
                "header": {
                    "values": [
                        "Monitoring Group",
                        "Service",
                        "Executions",
                        "Success",
                        "Failures",
                        "Warnings",
                    ]
                },
                "rows": [
                    {
                        "values": [
                            group_name,
                            resource_type,
                            item[group_name][resource_type]["summary"]["Executions"],
                            item[group_name][resource_type]["summary"]["Success"],
                            item[group_name][resource_type]["summary"]["Failures"],
                            item[group_name][resource_type]["summary"]["Warnings"],
                        ],
                        "style": item[group_name][resource_type]["summary"]["Status"],
                    }
                    for item in self.digest_data
                    for group_name in item
                    for resource_type in item[group_name]
                ],
            }
        }

    def _get_resource_table(self, runs_data: dict) -> dict:
        """Generates a digest table for specific monitoring group and resource type."""
        return {
            "table": {
                "header": {
                    "values": ["Resource Name"]
                    + list(next(iter(runs_data.values()))["values"].keys())
                },
                "rows": [
                    {
                        "values": [resource_name]
                        + list(runs_data[resource_name]["values"].values()),
                        "style": runs_data[resource_name]["Status"],
                    }
                    for resource_name in runs_data
                ],
            }
        }

    def generate_message_body(
        self, digest_start_time: datetime, digest_end_time: datetime
    ) -> list:
        """Generates message body for the digest report."""
        self.message_body.append({"text": "Digest Summary", "style": "header"})
        self.message_body.append(
            {
                "text": (
                    f"This report has been generated for the period from {digest_start_time.strftime('%B %d, %Y %I:%M %p')} "
                    f"to {digest_end_time.strftime('%B %d, %Y %I:%M %p')}."
                ),
                "style": "h11",
            }
        )
        # summary table
        summary_table = self._get_summary_table()
        self.message_body.append(summary_table)

        # monitoriting-group-resource-type-level tables
        for item in self.digest_data:
            for monitoring_group in item:
                for resource_type in item[monitoring_group]:
                    runs_data = item[monitoring_group][resource_type]["runs"]
                    resource_type_name = " ".join(
                        x.capitalize() for x in resource_type.split("_")
                    )
                    resource_report_header = {
                        "text": f"{monitoring_group}: {resource_type_name}",
                        "style": "header",
                    }
                    self.message_body.append(resource_report_header)
                    resource_table = self._get_resource_table(runs_data)

                    self.message_body.append(resource_table)

        return self.message_body

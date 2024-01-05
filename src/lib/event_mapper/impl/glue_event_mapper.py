from .general_aws_event_mapper import GeneralAwsEventMapper
from ...settings import Settings
from ...core.constants import SettingConfigResourceTypes


class GlueEventMapper(GeneralAwsEventMapper):
    def __init__(self, settings: Settings):
        super().__init__(settings)

    def get_resource_name(self, event):
        return event["detail"]["jobName"]

    def get_service_name(self):
        return SettingConfigResourceTypes.GLUE_JOBS

    def get_event_severity(self, event):  # todo: implement
        return "Unknown"

    def get_message_body(self, event):
        message_body = []
        table = {}
        rows = []
        table["table"] = {}
        table["table"]["rows"] = rows
        message_body.append(table)

        style = "error" if event["detail"]["severity"] == "ERROR" else None

        rows.append(super().create_table_row(["AWS Account", event["account"]]))
        rows.append(super().create_table_row(["AWS Region", event["region"]]))
        rows.append(super().create_table_row(["Time", event["time"]]))
        rows.append(super().create_table_row(["Job Name", event["detail"]["jobName"]]))
        rows.append(
            super().create_table_row(["State", event["detail"]["state"]], style)
        )
        rows.append(super().create_table_row(["JobRunID", event["detail"]["jobRunId"]]))
        rows.append(super().create_table_row(["Message", event["detail"]["message"]]))

        return message_body

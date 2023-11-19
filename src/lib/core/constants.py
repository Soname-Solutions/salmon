class SettingFileNames:
    GENERAL_FILE_NAME = "general.json"
    MONITORING_GROUPS_FILE_NAME = "monitoring_groups.json"
    RECIPIENTS_FILE_NAME = "recipients.json"


class Settings:
    MONITORED_RESOURCES = [
        "glue_jobs",
        "glue_workflows",
        "lambda_functions",
        "step_functions",
    ]

class SettingFileNames:
    GENERAL = "general.json"
    MONITORING_GROUPS = "monitoring_groups.json"
    RECIPIENTS = "recipients.json"


class SettingConfigs:
    RESOURCE_TYPES = [
        "glue_jobs",
        "glue_workflows",
        "lambda_functions",
        "step_functions",
    ]


class NotificationType:
    ALERT = "alert"
    DIGEST = "digest"


class CDKDeployExclusions:
    LAMBDA_ASSET_EXCLUSIONS = [".venv/", "__pycache__/"]

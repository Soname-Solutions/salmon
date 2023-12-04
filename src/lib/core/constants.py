class SettingFileNames:
    GENERAL = "general.json"
    MONITORING_GROUPS = "monitoring_groups.json"
    RECIPIENTS = "recipients.json"
    REPLACEMENTS = "replacements.json"


class SettingConfigs:
    RESOURCE_TYPES = [
        "glue_jobs",
        "glue_workflows",
        "lambda_functions",
        "step_functions",
    ]


class TimestreamRetention:
    MagneticStoreRetentionPeriodInDays = "365"
    MemoryStoreRetentionPeriodInHours = "240"


class NotificationType:
    ALERT = "alert"
    DIGEST = "digest"


class CDKDeployExclusions:
    LAMBDA_ASSET_EXCLUSIONS = [".venv/", "__pycache__/"]

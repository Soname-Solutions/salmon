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

class TimestreamRetention:
    MagneticStoreRetentionPeriodInDays = "365"
    MemoryStoreRetentionPeriodInHours = "240"

class NotificationType:
    ALERT = "alert"
    DIGEST = "digest"


class CDKDeployExclusions:
    LAMBDA_ASSET_EXCLUSIONS = [".venv/", "__pycache__/"]

class CDKResourceNames:
    """ Contains 'meaningful' part of AWS resources names. 
    Specifically, ones referred in both, tooling and monitored accounts
    """
    IAMROLE_EXTRACT_METRICS_LAMBDA = "extract-metrics-lambda"


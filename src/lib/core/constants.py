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
    MemoryStoreRetentionPeriodInHours = "24"


class NotificationType:
    ALERT = "alert"
    DIGEST = "digest"


class CDKDeployExclusions:
    LAMBDA_ASSET_EXCLUSIONS = [".venv/", "__pycache__/"]


class CDKResourceNames:
    """Contains 'meaningful' part of AWS resources names.
    Specifically, ones referred in both, tooling and monitored accounts
    """

    EVENTBUS_ALERTING = "alerting"
    IAMROLE_EXTRACT_METRICS_LAMBDA = "extract-metrics-lambda"
    IAMROLE_MONITORED_ACC_PUT_EVENTS = "monitored-acc-put-events"
    IAMROLE_MONITORED_ACC_EXTRACT_METRICS = "monitored-acc-extract-metrics"

    TIMESTREAM_TABLE_METRICS = {
        "Glue": "glue-metrics",
        "GlueWorkflow": "glue-workflow-metrics",
        "Lambda": "lambda-metrics",
        "StepFunction": "step-function-metrics",
    }

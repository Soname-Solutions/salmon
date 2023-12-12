class SettingFileNames:
    GENERAL = "general.json"
    MONITORING_GROUPS = "monitoring_groups.json"
    RECIPIENTS = "recipients.json"
    REPLACEMENTS = "replacements.json"


class SettingConfigResourceTypes:
    GLUE_JOBS = "glue_jobs"
    GLUE_WORKFLOWS = "glue_workflows"
    LAMBDA_FUNCTIONS = "lambda_functions"
    STEP_FUNCTIONS = "step_functions"


class SettingConfigs:
    RESOURCE_TYPES = [
        SettingConfigResourceTypes.GLUE_JOBS,
        SettingConfigResourceTypes.GLUE_WORKFLOWS,
        SettingConfigResourceTypes.LAMBDA_FUNCTIONS,
        SettingConfigResourceTypes.STEP_FUNCTIONS,
    ]

    RESOURCE_TYPES_LINKED_AWS_SERVICES = {
        SettingConfigResourceTypes.GLUE_JOBS: "glue",
        SettingConfigResourceTypes.GLUE_WORKFLOWS: "glue",
        SettingConfigResourceTypes.LAMBDA_FUNCTIONS: "lambda",
        SettingConfigResourceTypes.STEP_FUNCTIONS: "states",
    }


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

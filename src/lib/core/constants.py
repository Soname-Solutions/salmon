class SettingFileNames:
    GENERAL = "general.json"
    MONITORING_GROUPS = "monitoring_groups.json"
    RECIPIENTS = "recipients.json"
    REPLACEMENTS = "replacements.json"


class SettingConfigResourceTypes:
    GLUE_JOBS = "glue_jobs"
    GLUE_WORKFLOWS = "glue_workflows"
    GLUE_CRAWLERS = "glue_crawlers"
    GLUE_DATA_CATALOGS = "glue_catalogs"
    GLUE_DATA_QUALITY = "glue_data_quality"
    LAMBDA_FUNCTIONS = "lambda_functions"
    STEP_FUNCTIONS = "step_functions"


class DeliveryMethodTypes:
    AWS_SES = "AWS_SES"
    AWS_SNS = "AWS_SNS"
    SMTP = "SMTP"


class SettingConfigs:
    RESOURCE_TYPES = [
        SettingConfigResourceTypes.GLUE_JOBS,
        SettingConfigResourceTypes.GLUE_WORKFLOWS,
        SettingConfigResourceTypes.GLUE_CRAWLERS,
        SettingConfigResourceTypes.GLUE_DATA_CATALOGS,
        SettingConfigResourceTypes.GLUE_DATA_QUALITY,
        SettingConfigResourceTypes.LAMBDA_FUNCTIONS,
        SettingConfigResourceTypes.STEP_FUNCTIONS,
    ]

    RESOURCE_TYPES_LINKED_AWS_SERVICES = {
        SettingConfigResourceTypes.GLUE_JOBS: "glue",
        SettingConfigResourceTypes.GLUE_WORKFLOWS: "glue",
        SettingConfigResourceTypes.GLUE_CRAWLERS: "glue",
        SettingConfigResourceTypes.GLUE_DATA_CATALOGS: "glue",
        SettingConfigResourceTypes.GLUE_DATA_QUALITY: "glue",
        SettingConfigResourceTypes.LAMBDA_FUNCTIONS: "lambda",
        SettingConfigResourceTypes.STEP_FUNCTIONS: "stepfunctions",
    }


class CloudWatchConfigs:
    QUERY_TIMEOUT_SECONDS = 60


class TimestreamRetention:
    MagneticStoreRetentionPeriodInDays = "365"
    MemoryStoreRetentionPeriodInHours = "24"


class NotificationType:
    ALERT = "alert"
    DIGEST = "digest"


class EventResult:
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class DigestSettings:
    STATUS_OK = "ok"
    STATUS_WARNING = "warning"
    STATUS_ERROR = "error"
    REPORT_PERIOD_HOURS = 24
    CRON_EXPRESSION = "cron(0 8 * * ? *)"


class CDKDeployExclusions:
    LAMBDA_ASSET_EXCLUSIONS = [".venv/", "__pycache__/"]


class CDKResourceNames:
    """Contains 'meaningful' part of AWS resources names.
    Specifically, ones referred in both, tooling and monitored accounts
    """

    EVENTBUS_ALERTING = "alerting"
    IAMROLE_DIGEST_LAMBDA = "digest-lambda"
    IAMROLE_EXTRACT_METRICS_LAMBDA = "extract-metrics-lambda"
    IAMROLE_MONITORED_ACC_PUT_EVENTS = "monitored-acc-put-events"
    IAMROLE_MONITORED_ACC_EXTRACT_METRICS = "monitored-acc-extract-metrics"


class GrafanaDefaultSettings:
    INSTANCE_TYPE = "t3.micro"
    BITNAMI_IMAGE = "bitnami-grafana-10.2.2-1-r02-linux-debian-11-x86_64-hvm-ebs-nami"

class SettingFileNames:
    GENERAL_FILE_NAME = "general.json"
    MONITORING_GROUPS_FILE_NAME = "monitoring_groups.json"
    RECIPIENTS_FILE_NAME = "recipients.json"


class NotificationServiceConfig:
    SES_SENDER = "my_email@soname.de"
    ALERT_HEADER = "SDM [DEV] SAP Lean Glue Failure"
    SMTP_SENDER = "my_email@soname.de"

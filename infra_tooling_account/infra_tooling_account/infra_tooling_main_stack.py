from aws_cdk import Stack
from constructs import Construct
from lib.settings.settings import Settings

from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack
from infra_tooling_account.infra_tooling_alerting_stack import InfraToolingAlertingStack
from infra_tooling_account.infra_tooling_monitoring_stack import InfraToolingMonitoringStack
from infra_tooling_account.infra_tooling_grafana_stack import InfraToolingGrafanaStack

class InfraToolingMainStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)
        self.settings: Settings = kwargs.pop("settings", None)

        super().__init__(scope, id, **kwargs)

        common_stack = InfraToolingCommonStack(
            self,
            f"cf-{self.project_name}-InfraToolingCommonStack-{self.stage_name}",
            stage_name=self.stage_name,
            project_name=self.project_name,
            settings=self.settings,
        )

        settings_bucket = common_stack.settings_bucket
        internal_error_topic = common_stack.internal_error_topic
        notification_queue = common_stack.notification_queue
        timestream_storage = common_stack.timestream_storage
        timestream_kms_key = common_stack.timestream_kms_key

        alerting_stack = InfraToolingAlertingStack(
            self,
            f"cf-{self.project_name}-InfraToolingAlertingStack-{self.stage_name}",
            settings_bucket = settings_bucket,
            internal_error_topic = internal_error_topic,
            notification_queue = notification_queue,
            stage_name=self.stage_name,
            project_name=self.project_name,
            settings=self.settings,
        )        
        alerting_stack.add_dependency(common_stack)

        alerting_bus = alerting_stack.alerting_bus
        

        monitoring_stack = InfraToolingMonitoringStack(
            self,
            f"cf-{self.project_name}-InfraToolingMonitoringStack-{self.stage_name}",
            settings_bucket = settings_bucket,
            internal_error_topic = internal_error_topic,
            notification_queue = notification_queue,
            timestream_storage = timestream_storage,
            timestream_kms_key = timestream_kms_key,
            alerting_bus = alerting_bus,
            stage_name=self.stage_name,
            project_name=self.project_name,
            settings=self.settings,            
        )    
        monitoring_stack.add_dependency(common_stack)    
        monitoring_stack.add_dependency(alerting_stack)

        if self.settings.get_grafana_settings():
            grafana_stack = InfraToolingGrafanaStack(
                self,
                f"cf-{self.project_name}-InfraToolingGrafanaStack-{self.stage_name}",
                stage_name=self.stage_name,
                project_name=self.project_name,
                settings=self.settings,
            )
            grafana_stack.add_dependency(common_stack)
            
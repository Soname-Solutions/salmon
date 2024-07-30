import os
from copy import deepcopy
from collections import defaultdict
from functools import cached_property
from fnmatch import fnmatch

from lib.aws import (
    AWSNaming,
    GlueManager,
    LambdaManager,
    S3Manager,
    StepFunctionsManager,
    StsManager,
)
import lib.core.file_manager as fm
import lib.core.json_utils as ju
from lib.core.constants import (
    SettingConfigResourceTypes,
    SettingConfigs,
    SettingFileNames,
    NotificationType,
    GrafanaDefaultSettings,
    DigestSettings,
)

# Used for settings only
RESOURCE_TYPES_LINKED_AWS_MANAGERS = {
    SettingConfigResourceTypes.GLUE_JOBS: GlueManager,
    SettingConfigResourceTypes.GLUE_WORKFLOWS: GlueManager,
    SettingConfigResourceTypes.GLUE_CRAWLERS: GlueManager,
    SettingConfigResourceTypes.GLUE_DATA_CATALOGS: GlueManager,
    SettingConfigResourceTypes.GLUE_DATA_QUALITY: GlueManager,
    SettingConfigResourceTypes.LAMBDA_FUNCTIONS: LambdaManager,
    SettingConfigResourceTypes.STEP_FUNCTIONS: StepFunctionsManager,
}


class SettingsException(Exception):
    """Exception raised during setting processing errors."""

    pass


class Settings:
    """Manages and processes settings.

    This class handles the initialization, processing, and retrieval of settings
    related to general configurations, monitoring groups, and recipients. It provides
    methods for accessing both raw and processed settings.

    Attributes:
        _raw_settings (dict): Raw configuration settings loaded from JSON files.
        _processed_settings (dict): Processed configuration settings with added defaults, replaced wildcards, etc.
        _replacements (dict): Replacement values for placeholders in settings.
        _iam_role_list_monitored_res (str): IAM role to get the list of glue jobs, workflows, etc. for the wildcards replacement.

    Methods:
        _nested_replace_placeholder: Recursive function to replace placeholder with its value inside any nested structure.
        _get_default_metrics_extractor_role_arn: Get the default IAM role ARN for metrics extraction.
        _get_all_resource_names: Get all resource names for all the monitored account IDs.
        _replace_wildcards: Replace wildcards with real resource names.
        _read_settings: Read settings from file.
        ---
        processed_settings: Retrieves the processed configuration settings with defaults.
        general: Retrieves the processed general settings.
        monitoring_groups: the processed monitoring groups settings (without replaced wildcards).
        processed_monitoring_groups: the processed monitoring groups settings (with replaced wildcards)
        recipients: Retrieves the processed recipients settings.
        ---
        get_monitored_account_ids: Get monitored account IDs.
        get_monitored_account_region_pairs: Get monitored account IDs and Regions.
        get_metrics_collection_cron_expression: Get metrics collection cron schedule.
        get_tooling_account_props: Returns account_id and region of the tooling environment.
        get_digest_report_settings: Returns Digest report period (hours) and cron schedule.
        get_grafana_settings: Returns Grafana related settings.
        get_monitored_environment_name: Get monitored environment name by account ID and region.
        ---
        get_monitored_environment_props: Get monitored environment properties (account_id and region) by environment name.
        list_monitoring_groups: List monitoring groups.
        get_monitoring_group_content: Get monitoring group content.
        get_monitoring_groups: Get monitoring groups by resources list.
        get_monitoring_groups_by_resource_type: Get monitoring groups by resource type.
        get_recipients: Get recipients by monitoring groups.
        get_recipients_and_groups_by_notification_type: Get recepients and their monitoring groups by notification type.
        get_delivery_method: Get delivery method by name.
        ---
        from_file_path: Create an instance of Settings from local file paths.
        from_s3_path: Create an instance of Settings from S3 bucket paths.

    """

    def __init__(
        self,
        general_settings: str,
        monitoring_settings: str,
        recipients_settings: str,
        replacements_settings: str,
        iam_role_list_monitored_res: str,
    ):
        general = ju.parse_json(general_settings)
        monitoring = ju.parse_json(monitoring_settings)
        recipients = ju.parse_json(recipients_settings)

        self._raw_settings = {
            SettingFileNames.GENERAL: general,
            SettingFileNames.MONITORING_GROUPS: monitoring,
            SettingFileNames.RECIPIENTS: recipients,
        }
        self._processed_settings = {
            SettingFileNames.GENERAL: general,
            SettingFileNames.MONITORING_GROUPS: monitoring,
            SettingFileNames.RECIPIENTS: recipients,
        }
        self._replacements = (
            ju.parse_json(replacements_settings) if replacements_settings else {}
        )
        self._iam_role_list_monitored_res = iam_role_list_monitored_res

    @cached_property
    def processed_settings(self):
        # Replace placeholders
        if self._replacements:
            self._processed_settings = ju.replace_values_in_json(
                self._processed_settings, self._replacements
            )
        # Add default metrics_extractor_role_arn
        for m_env in self._processed_settings[SettingFileNames.GENERAL].get(
            "monitored_environments", []
        ):
            if "metrics_extractor_role_arn" not in m_env:
                m_env[
                    "metrics_extractor_role_arn"
                ] = self._get_default_metrics_extractor_role_arn(m_env["account_id"])

        # Add default sla_seconds and minimum_number_of_runs
        for m_env in self._processed_settings[SettingFileNames.MONITORING_GROUPS].get(
            "monitoring_groups", []
        ):
            for m_res in SettingConfigs.RESOURCE_TYPES:
                for res in m_env.get(m_res, []):
                    if "sla_seconds" not in res:
                        res["sla_seconds"] = 0
                    if "minimum_number_of_runs" not in res:
                        res["minimum_number_of_runs"] = 0

        # Add default settings for the digest report
        self._processed_settings[SettingFileNames.GENERAL][
            "tooling_environment"
        ].setdefault("digest_report_period_hours", DigestSettings.REPORT_PERIOD_HOURS)
        self._processed_settings[SettingFileNames.GENERAL][
            "tooling_environment"
        ].setdefault("digest_cron_expression", DigestSettings.CRON_EXPRESSION)

        # Add Grafana default settings
        grafana_instance_settings = self._processed_settings[SettingFileNames.GENERAL][
            "tooling_environment"
        ].get("grafana_instance", {})
        if grafana_instance_settings:
            grafana_instance_settings.setdefault(
                "grafana_bitnami_image", GrafanaDefaultSettings.BITNAMI_IMAGE
            )
            grafana_instance_settings.setdefault(
                "grafana_instance_type", GrafanaDefaultSettings.INSTANCE_TYPE
            )

        return self._processed_settings

    @property
    def general(self):
        return self.processed_settings[SettingFileNames.GENERAL]

    @property
    def monitoring_groups(self):
        """monitoring_groups without wildcards replacement"""
        return self.processed_settings[SettingFileNames.MONITORING_GROUPS]

    @cached_property
    def processed_monitoring_groups(self):
        """monitoring_groups with wildcards replacement"""
        self._process_monitoring_groups()
        return self.processed_settings[SettingFileNames.MONITORING_GROUPS]

    @property
    def recipients(self):
        return self.processed_settings[SettingFileNames.RECIPIENTS]

    # Processing methods
    def _get_default_metrics_extractor_role_arn(self, account_id: str) -> str:
        return f"arn:aws:iam::{account_id}:role/role-salmon-cross-account-extract-metrics-dev"

    def _process_monitoring_groups(self):
        # Get resource names dict
        resource_names = self._get_all_resource_names()

        # Replace wildcards for all the resource types (glue, lambda, etc.)
        for m_grp in self._processed_settings[SettingFileNames.MONITORING_GROUPS].get(
            "monitoring_groups", []
        ):
            for m_res in SettingConfigs.RESOURCE_TYPES:
                self._replace_wildcards(m_grp, m_res, resource_names[m_res])

    def _get_all_resource_names(self) -> dict:
        """Get all resource names for all the monitored account ids.
        Returns dict in the following format
            {"glue_jobs": {
                "monitored_env_name_1": ["job1", ...,  "jobN"],
                ...
                "monitored_env_name_N": ["job1", ...,  "jobN"]]
                },
            "glue_workflows": {...},
            ...
            }"""
        # Get all monitored accounts
        monitored_accounts = self.general.get("monitored_environments", [])

        # Initialize an empty dictionary for each resource type
        resource_names = defaultdict(dict)

        # Get all names for the resource type for all the monitored accounts
        for res_type in SettingConfigs.RESOURCE_TYPES:
            for account in monitored_accounts:
                account_name = account["name"]
                account_id = account["account_id"]
                region = account["region"]
                aws_client_name = SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                    res_type
                ]
                try:
                    if not self._iam_role_list_monitored_res:
                        raise SettingsException(
                            "IAM Role for metrics extraction not provided"
                        )

                    extract_metrics_role_arn = AWSNaming.Arn_IAMRole(
                        None,
                        account_id,
                        self._iam_role_list_monitored_res,
                    )
                except Exception as e:
                    raise SettingsException(
                        f"Error getting resource names for settings wildcards replacement: {e}"
                    )

                sts_manager = StsManager()
                client = sts_manager.get_client_via_assumed_role(
                    aws_client_name=aws_client_name,
                    via_assume_role_arn=extract_metrics_role_arn,
                    region=region,
                )

                manager = RESOURCE_TYPES_LINKED_AWS_MANAGERS[res_type](client)
                resource_names[res_type][account_name] = manager.get_all_names(
                    resource_type=res_type
                )

        return resource_names

    def _replace_wildcards(
        self, monitoring_group: dict, settings_key: str, replacements: dict
    ):
        """Replace wildcards with real resource names (which exist in monitored account)"""
        upd_mon_group = []
        for res in monitoring_group.get(settings_key, []):
            res_name = res["name"]
            res_monitored_env_name = res["monitored_environment_name"]
            if "*" in res_name:
                # Add new resources with full names
                for name in replacements[res_monitored_env_name]:
                    if fnmatch(name, res_name):
                        new_entry = deepcopy(res)
                        new_entry["name"] = name
                        upd_mon_group.append(new_entry)
            elif res_name in replacements[res_monitored_env_name]:
                new_entry = deepcopy(res)
                upd_mon_group.append(new_entry)
            # Data Quality Rulesets within Glue Jobs are not returned using list_data_quality_rulesets.
            # Consequently, wildcards do not work for them.
            # Therefore, we use the resource name as it is specified in the configuration.
            elif settings_key == SettingConfigResourceTypes.GLUE_DATA_QUALITY:
                new_entry = deepcopy(res)
                upd_mon_group.append(new_entry)

        if upd_mon_group:
            monitoring_group.pop(settings_key, None)
            monitoring_group[settings_key] = upd_mon_group

    # Get raw settings by file name
    def get_raw_settings(self, file_name: str) -> dict:
        """Get raw settings by file name"""
        return self._raw_settings[file_name]

    # CDK methods
    def get_monitored_account_ids(self) -> set[str]:
        """Get monitored account_ids"""
        return set(
            [
                m_env["account_id"]
                for m_env in self.processed_settings[SettingFileNames.GENERAL].get(
                    "monitored_environments", []
                )
            ]
        )

    def get_monitored_account_region_pairs(self) -> set[str]:
        """Get monitored account IDs and Regions"""
        monitored_environments = self.general.get("monitored_environments", [])
        monitored_account_region_pairs = {
            (m_env["account_id"], m_env["region"]) for m_env in monitored_environments
        }

        return monitored_account_region_pairs

    def get_metrics_collection_cron_expression(self) -> int:
        """Get metrics_collection_cron_expression"""
        return self.processed_settings[SettingFileNames.GENERAL]["tooling_environment"][
            "metrics_collection_cron_expression"
        ]

    def get_digest_report_settings(self) -> tuple[int, str]:
        """Get digest report settings"""
        digest_report_period_hours = self.general["tooling_environment"].get(
            "digest_report_period_hours"
        )
        digest_cron_expression = self.general["tooling_environment"].get(
            "digest_cron_expression"
        )
        return digest_report_period_hours, digest_cron_expression

    def get_grafana_settings(self) -> tuple[str, str, str, str, str]:
        """Get grafana settings"""
        grafana_settings = self.general["tooling_environment"].get("grafana_instance")
        if grafana_settings:
            return (
                grafana_settings.get("grafana_vpc_id"),
                grafana_settings.get("grafana_security_group_id"),
                grafana_settings.get("grafana_key_pair_name"),
                grafana_settings.get("grafana_bitnami_image"),
                grafana_settings.get("grafana_instance_type"),
            )
        return None

    def get_tooling_account_props(self) -> (str, str):
        """Returns account_id and region of tooling environment."""
        tooling = self.processed_settings[SettingFileNames.GENERAL].get(
            "tooling_environment"
        )
        return tooling.get("account_id"), tooling.get("region")

    # Lambda methods
    def get_monitored_environment_name(self, account_id: str, region: str) -> str:
        """Get monitored environment name by account_id and region."""
        for m_env in self.processed_settings[SettingFileNames.GENERAL].get(
            "monitored_environments", []
        ):
            if m_env["account_id"] == account_id and m_env["region"] == region:
                return m_env["name"]
        return None

    def get_monitored_environment_props(
        self, monitored_environment_name: str
    ) -> (str, str):
        """Get monitored environment properties (account_id and region) by env name."""
        for m_env in self.processed_settings[SettingFileNames.GENERAL].get(
            "monitored_environments", []
        ):
            if m_env["name"] == monitored_environment_name:
                return m_env["account_id"], m_env["region"]
        return None

    def list_monitoring_groups(self) -> list[str]:
        """List monitoring groups"""
        return [
            group["group_name"]
            for group in self.monitoring_groups.get("monitoring_groups", [])
        ]

    def get_monitoring_group_content(self, group_name: str) -> dict:
        """Get monitoring group content with replaced wildcards"""
        for group in self.processed_monitoring_groups.get("monitoring_groups", []):
            if group["group_name"] == group_name:
                return group
        return {}

    def get_monitoring_groups(self, resources: list[str]) -> list[str]:
        """Get monitoring groups by resources list."""
        matched_groups = set()  # Prevent duplicates

        for group in self.monitoring_groups.get("monitoring_groups", []):
            resource_groups = []
            for monitored_resource in SettingConfigs.RESOURCE_TYPES:
                resource_groups += group.get(monitored_resource, [])

            for resource in resources:
                matched_groups.update(
                    group["group_name"]
                    for res in resource_groups
                    if res["name"] and fnmatch(resource, res.get("name"))
                )

        return list(matched_groups)

    def get_monitoring_groups_by_resource_type(self, resource_type: str) -> list[str]:
        """Get monitoring groups related to particular resource type."""
        matched_groups = {
            group["group_name"]
            for group in self.monitoring_groups.get("monitoring_groups", [])
            if resource_type in group
        }
        return list(matched_groups)

    def get_recipients(
        self, monitoring_groups: list[str], notification_type: NotificationType
    ) -> list[dict]:
        """Get recipients by monitoring groups."""
        matched_recipients = []

        for recipient in self.recipients.get("recipients", []):
            subscriptions = recipient.get("subscriptions", [])
            for subscription in subscriptions:
                for monitoring_group in monitoring_groups:
                    if subscription.get("monitoring_group") == monitoring_group:
                        if (
                            notification_type == NotificationType.ALERT
                            and subscription.get("alerts")
                        ) or (
                            notification_type == NotificationType.DIGEST
                            and subscription.get("digest")
                        ):
                            recipient_info = {
                                "recipient": recipient.get("recipient"),
                                "delivery_method": recipient.get("delivery_method"),
                            }
                            if recipient_info not in matched_recipients:
                                matched_recipients.append(recipient_info)

        return matched_recipients

    def get_recipients_and_groups_by_notification_type(
        self, notification_type: NotificationType
    ) -> list[dict]:
        """Get all recipients and their monitoring groups by the notification type."""
        recipients_and_monitoring_groups = [
            {
                "recipient": recipient["recipient"],
                "delivery_method": recipient["delivery_method"],
                "monitoring_groups": [
                    subscription.get("monitoring_group")
                    for subscription in recipient.get("subscriptions", [])
                    if (
                        notification_type == NotificationType.ALERT
                        and subscription.get("alerts")
                    )
                    or (
                        notification_type == NotificationType.DIGEST
                        and subscription.get("digest")
                    )
                ],
            }
            for recipient in self.recipients.get("recipients", [])
        ]

        return recipients_and_monitoring_groups

    def get_delivery_method(self, delivery_method_name: str) -> dict:
        """Get delivery method by name

        Args:
            delivery_method_name (str): Name of the delivery method

        Returns:
            dict: Delivery method info
        """
        for method in self.general.get("delivery_methods", []):
            if method.get("name") == delivery_method_name:
                return method
        return {}

    @staticmethod
    def _read_settings(base_path: str, read_file_func, *file_names):
        settings = []
        for file_name in file_names:
            try:
                file_content = read_file_func(os.path.join(base_path, file_name))
                settings.append(file_content)
            except FileNotFoundError as e:
                if file_name == SettingFileNames.REPLACEMENTS:
                    settings.append(None)
                else:
                    raise e
        return settings

    @classmethod
    def from_file_path(cls, base_path: str, iam_role_list_monitored_res: str = None):
        (
            general_settings,
            monitoring_settings,
            recipients_settings,
            replacements_settings,
        ) = cls._read_settings(
            base_path,
            fm.read_file,
            SettingFileNames.GENERAL,
            SettingFileNames.MONITORING_GROUPS,
            SettingFileNames.RECIPIENTS,
            SettingFileNames.REPLACEMENTS,
        )
        return cls(
            general_settings,
            monitoring_settings,
            recipients_settings,
            replacements_settings,
            iam_role_list_monitored_res,
        )

    @classmethod
    def from_s3_path(cls, base_path: str, iam_role_list_monitored_res: str = None):
        s3 = S3Manager()
        (
            general_settings,
            monitoring_settings,
            recipients_settings,
            replacements_settings,
        ) = cls._read_settings(
            base_path,
            s3.read_file,
            SettingFileNames.GENERAL,
            SettingFileNames.MONITORING_GROUPS,
            SettingFileNames.RECIPIENTS,
            SettingFileNames.REPLACEMENTS,
        )
        return cls(
            general_settings,
            monitoring_settings,
            recipients_settings,
            replacements_settings,
            iam_role_list_monitored_res,
        )

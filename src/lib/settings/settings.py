import os
from copy import deepcopy
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
)

# Used for settings only
RESOURCE_TYPES_LINKED_AWS_MANAGERS = {
    SettingConfigResourceTypes.GLUE_JOBS: GlueManager,
    SettingConfigResourceTypes.GLUE_WORKFLOWS: GlueManager,
    SettingConfigResourceTypes.LAMBDA_FUNCTIONS: LambdaManager,
    SettingConfigResourceTypes.STEP_FUNCTIONS: StepFunctionsManager,
}


class Settings:
    """Manages and processes settings.

    This class handles the initialization, processing, and retrieval of settings
    related to general configurations, monitoring groups, and recipients. It provides
    methods for accessing both raw and processed settings.

    Attributes:
        _raw_settings (dict): Raw configuration settings loaded from JSON files.
        _processed_settings (dict): Processed configuration settings with added defaults, replaced wildcards, etc.
        _replacements (dict): Replacement values for placeholders in settings.
        _iam_role_extract_metrics (str): IAM role to get the list of glue jobs, workflows, etc. for the wildcards replacement.

    Methods:
        _nested_replace_placeholder: Recursive function to replace placeholder with its value inside any nested structure.
        _get_default_metrics_extractor_role_arn: Get the default IAM role ARN for metrics extraction.
        _get_all_resource_names: Get all resource names for all the monitored account IDs.
        _replace_wildcards: Replace wildcards with real resource names.
        _read_settings: Read settings from file.
        ---
        processed_settings: Retrieves the processed configuration settings with defaults.
        general: Retrieves the processed general settings.
        monitoring_groups: Retrieves the processed monitoring groups settings.
        recipients: Retrieves the processed recipients settings.
        ---
        get_monitored_account_ids: Get monitored account IDs.
        get_metrics_collection_interval_min: Get metrics collection interval.
        get_tooling_account_props: Returns account_id and region of the tooling environment.
        get_monitored_environment_name: Get monitored environment name by account ID and region.
        ---
        get_monitored_environment_props: Get monitored environment properties (account_id and region) by environment name.
        list_monitoring_groups: List monitoring groups.
        get_monitoring_group_content: Get monitoring group content.
        get_monitoring_groups: Get monitoring groups by resources list.
        get_recipients: Get recipients by monitoring groups.
        get_sender_email: Get sender email per delivery method.
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
        iam_role_extract_metrics: str,
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
        self._iam_role_extract_metrics = iam_role_extract_metrics

    @cached_property
    def processed_settings(self):
        # Replace placeholders
        for key, value in self._replacements.items():
            placeholder = f"<<{key}>>"
            self._processed_settings = self._nested_replace_placeholder(
                self._processed_settings, placeholder, value
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

        return self._processed_settings

    @property
    def general(self):
        return self.processed_settings[SettingFileNames.GENERAL]

    @cached_property
    def monitoring_groups(self):
        # Get resource names dict
        resource_names = self._get_all_resource_names()

        # Replace wildcards for all the resource types (glue, lambda, etc.)
        for m_env in self._processed_settings[SettingFileNames.MONITORING_GROUPS].get(
            "monitoring_groups", []
        ):
            for m_res in SettingConfigs.RESOURCE_TYPES:
                self._replace_wildcards(m_env, m_res, resource_names[m_res])

        return self.processed_settings[SettingFileNames.MONITORING_GROUPS]

    @property
    def recipients(self):
        return self.processed_settings[SettingFileNames.RECIPIENTS]

    # Processing methods
    def _nested_replace_placeholder(self, config, placeholder, replacement):
        """Recursive function to replace placeholder with its value inside any nested structure"""
        if type(config) == list:
            return [
                self._nested_replace_placeholder(item, placeholder, replacement)
                for item in config
            ]

        if type(config) == dict:
            return {
                key: self._nested_replace_placeholder(value, placeholder, replacement)
                for key, value in config.items()
            }

        if type(config) == str:
            return config.replace(placeholder, replacement)
        else:
            return config

    def _get_default_metrics_extractor_role_arn(self, account_id: str) -> str:
        return f"arn:aws:iam::{account_id}:role/role-salmon-cross-account-extract-metrics-dev"

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
        resource_names = dict()
        for res_type in SettingConfigs.RESOURCE_TYPES:
            resource_names[res_type] = {}

        # Get all names for the resource type for all the monitored accounts
        for res_type in SettingConfigs.RESOURCE_TYPES:
            for account in monitored_accounts:
                account_name = account["name"]
                account_id = account["account_id"]
                region = account["region"]
                aws_client_name = SettingConfigs.RESOURCE_TYPES_LINKED_AWS_SERVICES[
                    res_type
                ]
                extract_metrics_role_arn = AWSNaming.Arn_IAMRole(
                    None,
                    account_id,
                    self._iam_role_extract_metrics,
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
        self, monitoring_group: list, settings_key: str, replacements: dict
    ):
        """Replace wildcards with real resource names (which exist in monitored account)"""
        for res in monitoring_group.get(settings_key, []):
            res_name = res["name"]
            res_monitored_env_name = res["monitored_environment_name"]
            if "*" in res_name:
                # Add new resources with full names
                for name in replacements[res_monitored_env_name]:
                    if fnmatch(name, res_name):
                        new_entry = deepcopy(res)
                        new_entry["name"] = name
                        monitoring_group[settings_key].append(new_entry)
                # Remove the wildcard entry
                monitoring_group[settings_key].remove(res)
            elif res_name not in replacements[res_monitored_env_name]:
                # Remove resource if it does not exist in the account
                monitoring_group[settings_key].remove(res)

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

    def get_metrics_collection_interval_min(self) -> int:
        """Get metrics_collection_interval_min"""
        return self.processed_settings[SettingFileNames.GENERAL]["tooling_environment"][
            "metrics_collection_interval_min"
        ]

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
        """Get monitoring group content"""
        for group in self.monitoring_groups.get("monitoring_groups", []):
            if group["group_name"] == group_name:
                return group
        return None

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
                    # TODO: replace fnmatch with == when _process_monitoring_groups() implemented
                    if res["name"] and fnmatch(resource, res.get("name"))
                )

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

    def get_sender_email(self, delivery_method: str) -> str:
        """Get sender email per delivery method"""
        for method in self.general.get("delivery_methods", []):
            if method.get("name") == delivery_method:
                return method.get("sender_email", None)
        return None

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
    def from_file_path(cls, base_path: str, iam_role_extract_metrics: str = None):
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
            iam_role_extract_metrics,
        )

    @classmethod
    def from_s3_path(cls, base_path: str, iam_role_extract_metrics: str = None):
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
            iam_role_extract_metrics,
        )

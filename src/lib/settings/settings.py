import os
from typing import List
from functools import cached_property
from fnmatch import fnmatch

import lib.core.file_manager as fm
import lib.core.json_utils as ju
from lib.core.constants import SettingConfigs, SettingFileNames, NotificationType
from lib.aws.s3_manager import S3Manager


class Settings:
    """Manages and processes settings.

    This class handles the initialization, processing, and retrieval of settings
    related to general configurations, monitoring groups, and recipients. It provides
    methods for accessing both raw and processed settings.

    Attributes:
        _raw_settings (dict): Raw configuration settings loaded from JSON files.
        _processed_settings (dict): Processed configuration settings with added defaults, replaced wildcards, etc..

    Methods:
        processed_settings: Retrieves the processed configuration settings with defaults.
        general: Retrieves the processed general settings.
        monitoring_groups: Retrieves the processed monitoring groups settings.
        recipients: Retrieves the processed recipients settings.
        get_raw_settings: Retrieves raw settings by file name.
        ----
        get_monitored_account_ids: Retrieves monitored account IDs.
        get_metrics_collection_interval_min: Retrieves metrics collection interval.
        get_monitored_environment_name: Retrieves monitored environment name by account ID and region.
        get_monitoring_groups: Retrieves monitoring groups by resource names.
        get_recipients: Retrieves recipients for specified monitoring groups and notification type.
        ----
        get_monitored_environment_names_raw_gs: Retrieves monitored environment names from raw general settings.
        get_monitored_account_id_and_region_raw_gs: Retrieves monitored environments 'account_id|region' from raw general settings.
        get_delivery_method_names_raw_gs: Retrieves delivery method names from raw general settings.
        get_monitoring_group_names_raw_mgs: Retrieves group names from raw monitoring groups settings.
        get_monitored_environment_names_raw_mgs: Retrieves monitored environment names from raw monitoring groups settings.
        get_monitoring_group_names_raw_rs: Retrieves monitoring group names from raw recipients settings.
        get_delivery_method_names_raw_rs: Retrieves delivery method names from raw recipients settings.
        from_file_path: Creates an instance of Settings from local file paths.
        from_s3_path: Creates an instance of Settings from S3 bucket paths.

    """

    def __init__(
        self, general_settings: str, monitoring_settings: str, recipients_settings: str
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

    @cached_property
    def processed_settings(self):
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
        self._process_monitoring_groups()
        return self.processed_settings[SettingFileNames.MONITORING_GROUPS]

    @property
    def recipients(self):
        return self.processed_settings[SettingFileNames.RECIPIENTS]

    # Processing methods
    def _get_default_metrics_extractor_role_arn(self, account_id: str) -> str:
        return f"arn:aws:iam::{account_id}:role/role-salmon-cross-account-extract-metrics-dev"

    def _process_monitoring_groups(self):
        # TODO: add wildcards replacement for all the resource types (glue, lambda, etc.)
        pass

    # Get raw settings by file name
    def get_raw_settings(self, file_name: str) -> dict:
        """Get raw settings by file name"""
        return self._raw_settings[file_name]

    # CDK methods
    def get_monitored_account_ids(self) -> List[str]:
        """Get monitored account_ids"""
        return set([
            m_env["account_id"]
            for m_env in self.processed_settings[SettingFileNames.GENERAL].get(
                "monitored_environments", []
            )
        ])

    def get_metrics_collection_interval_min(self) -> int:
        """Get metrics_collection_interval_min"""
        return self.processed_settings[SettingFileNames.GENERAL]["tooling_environment"][
            "metrics_collection_interval_min"
        ]

    def get_tooling_account_props(self) -> str:
        """Returns account_id and region of tooling environment."""
        tooling = self.processed_settings[SettingFileNames.GENERAL].get("tooling_environment")
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

    def get_monitoring_groups(self, resources: List[str]) -> List[str]:
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
        self, monitoring_groups: List[str], notification_type: NotificationType
    ) -> List[dict]:
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

    @staticmethod
    def _read_settings(base_path: str, read_file_func, *file_names):
        return [
            read_file_func(os.path.join(base_path, file_name))
            for file_name in file_names
        ]

    @classmethod
    def from_file_path(cls, base_path: str):
        general_settings, monitoring_settings, recipients_settings = cls._read_settings(
            base_path,
            fm.read_file,
            SettingFileNames.GENERAL,
            SettingFileNames.MONITORING_GROUPS,
            SettingFileNames.RECIPIENTS,
        )
        return cls(general_settings, monitoring_settings, recipients_settings)

    @classmethod
    def from_s3_path(cls, base_path: str):
        s3 = S3Manager()
        general_settings, monitoring_settings, recipients_settings = cls._read_settings(
            base_path,
            s3.read_file,
            SettingFileNames.GENERAL,
            SettingFileNames.MONITORING_GROUPS,
            SettingFileNames.RECIPIENTS,
        )
        return cls(general_settings, monitoring_settings, recipients_settings)

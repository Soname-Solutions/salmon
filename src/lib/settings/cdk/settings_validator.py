from typing import List
import os
import jsonschema

import lib.core.file_manager as fm
import lib.core.json_utils as ju
from lib.core.constants import SettingFileNames, SettingConfigs
from lib.settings import Settings

validator_dir = os.path.dirname(os.path.abspath(__file__))
SCHEMA_FILES_PATH = os.path.join(validator_dir, "schemas")

ERRORS_SEP = "\n\n--------------------------------------------------------------\n\n"


class SettingsValidatorException(Exception):
    """Exception raised for errors during settings validation."""

    pass


# Main validation function
def validate(settings: Settings):
    """Validates settings for consistency.

    This function performs multiple validation checks on the provided settings.

    Raises:
        SettingsValidatorException: If any validation checks fail.

    """
    VALIDATION_RULES = [
        validate_schemas,
        validate_unique_monitored_environment_names_gs,
        validate_unique_monitored_accout_id_region_combinations_gs,
        validate_unique_monitoring_group_names_mgs,
        validate_existing_monitored_environment_names_mgs,
        validate_existing_monitoring_group_names_rs,
        validate_existing_delivery_methods_rs,
    ]
    errors = []

    for rule in VALIDATION_RULES:
        errors.extend(rule(settings))

    error_messages = [msg for msg, result in errors if not result]

    if error_messages:
        raise SettingsValidatorException(ERRORS_SEP.join(error_messages))


# Rules
def validate_schemas(settings: Settings) -> List[tuple]:
    """Validate setting raw JSON files against schema."""
    errors = []
    for attr_name, file_name in SettingFileNames.__dict__.items():
        if not attr_name.startswith("__") and attr_name != "REPLACEMENTS":
            schema_file = fm.read_file(os.path.join(SCHEMA_FILES_PATH, file_name))
            schema = ju.parse_json(schema_file)

            try:
                jsonschema.validate(settings.get_raw_settings(file_name), schema)
                errors.append(("", True))
            except jsonschema.ValidationError as e:
                errors.append(
                    (
                        f"JSON schema validation failed for {file_name} settings: {e}",
                        False,
                    )
                )

    return errors


def validate_unique_monitored_environment_names_gs(settings: Settings) -> List[tuple]:
    """Validates unique monitored environment names in General settings."""
    return validate_unique_names(
        get_monitored_environment_names_raw_gs(settings),
        "Monitored environment names are not unique in General settings.",
    )


def validate_unique_monitored_accout_id_region_combinations_gs(
    settings: Settings,
) -> List[tuple]:
    """Validates unique account_id + region combinations in monitored environments in General settings."""
    return validate_unique_names(
        get_monitored_account_id_and_region_raw_gs(settings),
        "Monitored environment account_id + region combinations are not unique in General settings.",
    )


def validate_unique_monitoring_group_names_mgs(settings: Settings) -> List[tuple]:
    """Validates unique monitoring group names in Monitoring Groups settings."""
    return validate_unique_names(
        get_monitoring_group_names_raw_mgs(settings),
        "Monitoring group names are not unique in Monitoring Groups settings.",
    )


def validate_existing_monitored_environment_names_mgs(
    settings: Settings,
) -> List[tuple]:
    """Validates if the monitored environment names in the Monitoring Groups settings
    match the ones in the General settings."""

    return validate_existing_names(
        get_monitored_environment_names_raw_mgs(settings),
        get_monitored_environment_names_raw_gs(settings),
        "monitored_environment_name in Monitoring Groups settings does not match General settings.",
    )


def validate_existing_monitoring_group_names_rs(settings: Settings) -> List[tuple]:
    """Validates if the monitoring group names in the Recipients settings
    match the ones in the Monitoring Groups settings."""
    return validate_existing_names(
        get_monitoring_group_names_raw_rs(settings),
        get_monitoring_group_names_raw_mgs(settings),
        "monitoring_group names in Recipients do not match Monitoring Groups settings.",
    )


def validate_existing_delivery_methods_rs(settings: Settings) -> List[tuple]:
    """Validates if the delivery methods in the Recipients settings
    match the ones in the General settings."""
    return validate_existing_names(
        get_delivery_method_names_raw_rs(settings),
        get_delivery_method_names_raw_gs(settings),
        "delivery_method in Recipients do not match General settings.",
    )


# Helpers
def validate_unique_names(names: List[str], error_message: str) -> List[tuple]:
    """Validates that names are unique."""
    seen_names = set()
    duplicate_names = set()

    for name in names:
        if name in seen_names:
            duplicate_names.add(name)
        else:
            seen_names.add(name)

    return [
        (f"Error: {error_message} Non-unique names :{duplicate_names}", False)
        if duplicate_names
        else ("", True)
    ]


def validate_existing_names(
    names: List[str], ref_names: List[str], error_message: str
) -> List[tuple]:
    """Validates that names match the ones in ref_names."""
    not_existing_names = [name for name in names if name not in ref_names]

    return [
        (f"Error: {error_message} Non-existing names :{set(not_existing_names)}", False)
        if not_existing_names
        else ("", True)
    ]


def validate_cdk_env_variables(
    env_name: str,
    cdk_env_variables: set[str],
    config_values: set[str],
):
    """
    Validates that the region and account ID in the configuration file (general.json)
    are aligned with the current region and account ID determined by the AWS CDK.

    Args:
        env_name (str): The name of the environment.
        cdk_env_variables set[str]: The account and region determined by the AWS CDK.
        config_values set[str]: The set of account and region pairs from the configuration file.

    Returns:
        bool: True if the account and region are aligned, False otherwise.
    """
    if not cdk_env_variables.issubset(config_values):
        raise SettingsValidatorException(
            f"Error: The account and region {config_values} set for the {env_name} in the general.json configuration file "
            f"are not aligned with the current account and region {cdk_env_variables} determined by the AWS CDK."
        )
    return True


# Methods for validation rules (work with raw settings)
def get_monitored_environment_names_raw_gs(settings) -> List[str]:
    """Retrieves the monitored_environment names from the General settings (raw)."""
    return [
        m_env["name"]
        for m_env in settings.get_raw_settings(SettingFileNames.GENERAL).get(
            "monitored_environments", []
        )
    ]


def get_monitored_account_id_and_region_raw_gs(settings) -> List[str]:
    """Retrieves the monitored environments 'account_id|region' from the General settings (raw)."""
    return [
        f"""{m_env["account_id"]}|{m_env["region"]}"""
        for m_env in settings.get_raw_settings(SettingFileNames.GENERAL).get(
            "monitored_environments", []
        )
    ]


def get_delivery_method_names_raw_gs(settings) -> List[str]:
    """Retrieves the delivery_method names from the General settings (raw)."""
    return [
        dlvry_mthd["name"]
        for dlvry_mthd in settings.get_raw_settings(SettingFileNames.GENERAL).get(
            "delivery_methods", []
        )
    ]


def get_monitoring_group_names_raw_mgs(settings) -> List[str]:
    """Retrieves the group_names from the Monitoring Groups settings (raw)."""
    return [
        m_grp["group_name"]
        for m_grp in settings.get_raw_settings(SettingFileNames.MONITORING_GROUPS).get(
            "monitoring_groups", []
        )
    ]


def get_monitored_environment_names_raw_mgs(settings) -> List[str]:
    """Retrieves the monitored_environment_names from the Monitoring settings (raw)."""
    resource_groups = []
    for group in settings.get_raw_settings(SettingFileNames.MONITORING_GROUPS).get(
        "monitoring_groups", []
    ):
        for m_res in SettingConfigs.RESOURCE_TYPES:
            resource_groups.extend(group.get(m_res, []))

    return [res.get("monitored_environment_name") for res in resource_groups]


def get_monitoring_group_names_raw_rs(settings) -> List[str]:
    """Retrieves the monitoring_group names from the Recipients settings (raw)."""
    return [
        subscription["monitoring_group"]
        for rec in settings.get_raw_settings(SettingFileNames.RECIPIENTS).get(
            "recipients", []
        )
        for subscription in rec.get("subscriptions", [])
    ]


def get_delivery_method_names_raw_rs(settings) -> List[str]:
    """Retrieves the delivery_method names from the Recipients settings (raw)."""
    return [
        rec["delivery_method"]
        for rec in settings.get_raw_settings(SettingFileNames.RECIPIENTS).get(
            "recipients", []
        )
    ]

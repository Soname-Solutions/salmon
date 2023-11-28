from typing import List
import os
import jsonschema

import lib.core.file_manager as fm
import lib.core.json_utils as ju
from lib.core.constants import SettingFileNames
from lib.settings import Settings

SCHEMA_FILES_PATH = "src/lib/settings/cdk/schemas/"
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


# Rules
def validate_schemas(settings: Settings) -> List[tuple]:
    """Validate setting raw JSON files against schema."""
    errors = []
    for attr_name, file_name in SettingFileNames.__dict__.items():
        if not attr_name.startswith("__"):
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
        settings.get_monitored_environment_names_raw_gs(),
        "Monitored environment names are not unique in General settings.",
    )


def validate_unique_monitored_accout_id_region_combinations_gs(
    settings: Settings,
) -> List[tuple]:
    """Validates unique account_id + region combinations in monitored environments in General settings."""
    return validate_unique_names(
        settings.get_monitored_account_id_and_region_raw_gs(),
        "Monitored environment account_id + region combinations are not unique in General settings.",
    )


def validate_unique_monitoring_group_names_mgs(settings: Settings) -> List[tuple]:
    """Validates unique monitoring group names in Monitoring Groups settings."""
    return validate_unique_names(
        settings.get_monitoring_group_names_raw_mgs(),
        "Monitoring group names are not unique in Monitoring Groups settings.",
    )


def validate_existing_monitored_environment_names_mgs(
    settings: Settings,
) -> List[tuple]:
    """Validates if the monitored environment names in the Monitoring Groups settings
    match the ones in the General settings."""

    return validate_existing_names(
        settings.get_monitored_environment_names_raw_mgs(),
        settings.get_monitored_environment_names_raw_gs(),
        "monitored_environment_name in Monitoring Groups settings does not match General settings.",
    )


def validate_existing_monitoring_group_names_rs(settings: Settings) -> List[tuple]:
    """Validates if the monitoring group names in the Recipients settings
    match the ones in the Monitoring Groups settings."""
    return validate_existing_names(
        settings.get_monitoring_group_names_raw_rs(),
        settings.get_monitoring_group_names_raw_mgs(),
        "monitoring_group names in Recipients do not match Monitoring Groups settings.",
    )


def validate_existing_delivery_methods_rs(settings: Settings) -> List[tuple]:
    """Validates if the delivery methods in the Recipients settings
    match the ones in the General settings."""
    return validate_existing_names(
        settings.get_delivery_method_names_raw_rs(),
        settings.get_delivery_method_names_raw_gs(),
        "delivery_method in Recipients do not match General settings.",
    )

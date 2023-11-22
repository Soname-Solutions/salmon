from lib.settings.settings_reader import (
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)


class SettingsValidatorException(Exception):
    """Exception raised for errors during settings validation."""

    pass


# Main validation function
def validate(
    general_settings: GeneralSettingsReader,
    monitoring_group_settings: MonitoringSettingsReader,
    recipient_settings: RecipientsSettingsReader,
):
    """Validates settings for consistency.

    This function performs multiple validation checks on the provided settings.

    Args:
        general (GeneralSettingsReader): The General settings reader.
        monitoring_groups (MonitoringSettingsReader): The Monitoring Groups settings reader.
        recipients (RecipientsSettingsReader): The Recipients settings reader.

    Raises:
        SettingsValidatorException: If any validation checks fail.

    """
    VALIDATION_RULES = [
        validate_unique_monitored_environment_names,
        validate_unique_monitoring_group_names,
        validate_monitored_environment_name_for_monitoring_groups,
        validate_monitoring_group_name_for_recipients,
        validate_delivery_method_for_recipients,
    ]
    errors = []

    for rule in VALIDATION_RULES:
        errors.append(
            rule(
                general_settings=general_settings,
                monitoring_group_settings=monitoring_group_settings,
                recipient_settings=recipient_settings,
            )
        )

    error_messages = [msg for msg, result in errors if not result]

    if error_messages:
        raise SettingsValidatorException("\n".join(error_messages))


def validate_unique_names(func: object, error_message: str) -> tuple:
    """Validates that names are unique.

    This function checks if the names obtained from the specified function within the
    given settings are unique.

    Args:
        func (object): The function to retrieve names from the settings.
        error_message (str): Custom error message for the validation.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    names = func()
    seen_names = set()
    duplicate_names = set()

    for name in names:
        if name in seen_names:
            duplicate_names.add(name)
        else:
            seen_names.add(name)

    return (
        (f"Error: {error_message} Non-unique names :{duplicate_names}", False)
        if duplicate_names
        else ("", True)
    )


# Rules
def validate_unique_monitored_environment_names(**kwargs) -> tuple:
    """Validates unique monitored environment names.

    This function checks if the monitored environment names in the General settings are unique.

    Args:
        **kwargs: SettingReader objects.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    return validate_unique_names(
        kwargs.get("general_settings").get_monitored_environment_names,
        "Monitored environment names are not unique in General config.",
    )


def validate_unique_monitoring_group_names(**kwargs) -> tuple:
    """Validates unique monitoring group names.

    This function checks if the monitoring group names in the Monitoring Groups settings are unique.

    Args:
        **kwargs: SettingReader objects.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    return validate_unique_names(
        kwargs.get("monitoring_group_settings").get_monitoring_group_names,
        "Monitoring group names are not unique in Monitoring Groups config.",
    )


def validate_monitored_environment_name_for_monitoring_groups(**kwargs) -> tuple:
    """Validates monitored environment names for monitoring groups.

    This function checks if the monitored environment names in the Monitoring Groups settings
    match the ones in the General settings.

    Args:
        **kwargs: SettingReader objects.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    not_existing_names = set()
    monitored_environment_names = kwargs.get(
        "monitoring_group_settings"
    ).get_monitored_environment_names()

    for m_env_name in monitored_environment_names:
        if (
            m_env_name
            not in kwargs.get("general_settings").get_monitored_environment_names()
        ):
            not_existing_names.add(m_env_name)

    return (
        (
            f"Error: monitored_environment_name in Monitoring Groups config do not match General config. Not existing names :{not_existing_names}",
            False,
        )
        if not_existing_names
        else ("", True)
    )


def validate_monitoring_group_name_for_recipients(**kwargs) -> tuple:
    """Validates monitoring group names for recipients.

    This function checks if the monitoring group names in the Recipients settings
    match the ones in the Monitoring Groups settings.

    Args:
        **kwargs: SettingReader objects.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    not_existing_names = set()
    monitoring_group_names = kwargs.get(
        "recipient_settings"
    ).get_monitoring_group_names()

    for m_grp_name in monitoring_group_names:
        if (
            m_grp_name
            not in kwargs.get("monitoring_group_settings").get_monitoring_group_names()
        ):
            not_existing_names.add(m_grp_name)

    return (
        (
            f"Error: monitoring_group names in Recipients do not match Monitoring Groups config. Not existing names :{not_existing_names}",
            False,
        )
        if not_existing_names
        else ("", True)
    )


def validate_delivery_method_for_recipients(**kwargs) -> tuple:
    """Validates delivery methods for recipients.

    This function checks if the delivery methods in the Recipients settings
    match the ones in the General settings.

    Args:
        **kwargs: SettingReader objects.

    Returns:
        tuple: Error message and boolean result. Empty message if validation passes.

    """
    not_existing_methods = set()
    delivery_method_names = kwargs.get("recipient_settings").get_delivery_method_names()

    for dlvry_mthd in delivery_method_names:
        if dlvry_mthd not in kwargs.get("general_settings").get_delivery_method_names():
            not_existing_methods.add(dlvry_mthd)

    return (
        (
            f"Error: Delivery methods in Recipients do not match General config. Not existing methods :{not_existing_methods}",
            False,
        )
        if not_existing_methods
        else ("", True)
    )

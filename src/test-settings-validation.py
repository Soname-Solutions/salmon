import os

from lib.core import file_manager as fm
from lib.core import json_utils as ju
from lib.core import jsonschema_utils as js
from lib.core.constants import SettingFileNames

from lib.settings.settings_reader import (
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)
from lib.settings.settings_validator import validate


def test_settings_validation():
    """Test settings validation.

    This function performs both schema and business validation on the test settings.
    It reads the settings and schemas from specified paths, validates the JSON schemas,
    and then performs business validation using the validate function.

    Raises:
        jsonschema.exceptions.ValidationError: If any schema validation checks fail.
        SettingsValidatorException: If any business validation checks fail.

    """
    schema_base_path = "src/schemas/"
    config_base_path = "./config/sample_settings/"

    # Settings
    general = GeneralSettingsReader(
        SettingFileNames.GENERAL_FILE_NAME,
        fm.read_file(
            os.path.join(config_base_path, SettingFileNames.GENERAL_FILE_NAME)
        ),
    )
    monitoring_groups = MonitoringSettingsReader(
        SettingFileNames.MONITORING_GROUPS_FILE_NAME,
        fm.read_file(
            os.path.join(config_base_path, SettingFileNames.MONITORING_GROUPS_FILE_NAME)
        ),
    )
    recipients = RecipientsSettingsReader(
        SettingFileNames.RECIPIENTS_FILE_NAME,
        fm.read_file(
            os.path.join(config_base_path, SettingFileNames.RECIPIENTS_FILE_NAME)
        ),
    )

    # Schemas
    general_schema = ju.parse_json(
        fm.read_file(os.path.join(schema_base_path, SettingFileNames.GENERAL_FILE_NAME))
    )
    monitoring_groups_schema = ju.parse_json(
        fm.read_file(
            os.path.join(schema_base_path, SettingFileNames.MONITORING_GROUPS_FILE_NAME)
        )
    )
    recipients_schema = ju.parse_json(
        fm.read_file(
            os.path.join(schema_base_path, SettingFileNames.RECIPIENTS_FILE_NAME)
        )
    )

    # Schema validation
    print("Start General schema validation")
    js.validate_json_schema(general.settings, general_schema)
    print("Start Monitoring Groups schema validation")
    js.validate_json_schema(monitoring_groups.settings, monitoring_groups_schema)
    print("Start Recipients schema validation")
    js.validate_json_schema(recipients.settings, recipients_schema)

    # Business validation
    print("Start business validation")
    validate(general, monitoring_groups, recipients)


if __name__ == "__main__":
    test_settings_validation()

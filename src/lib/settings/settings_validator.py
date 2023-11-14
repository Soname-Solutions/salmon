import jsonschema

from lib.settings.settings_reader.settings_reader import SettingsReader


class SettingsValidator:
    """Base class for settings validation.

    This class provides a common interface and shared business logic for validating setting files.

    Methods:
        validate_json_schema: Validates a JSON settings file against the schema.
        validate_business_logic: Performs custom business logic validation on the settings content.

    """

    def __init__(self):
        """SettingsValidator class constructor."""

    def validate_json_schema(self, settings_reader: SettingsReader, json_schema: dict):
        """Validates a JSON file against the schema.

        Args:
            settings_reader (dict): SettingsReader object containing the name and content of the setting file.
            json_schema (dict): The JSON schema to be used for validation.

        Raises:
            jsonschema.exceptions.ValidationError: If the JSON file does not match the schema.
        """
        try:
            jsonschema.validate(settings_reader.settings, json_schema)
        except jsonschema.exceptions.ValidationError as e:
            raise jsonschema.exceptions.ValidationError(
                f"JSON schema validation failed for '{settings_reader.settings_file_name}': {e}"
            )

    def validate_business_logic(self, json_data: str, other_config_data: str):
        """Performs custom business logic validation on the settings content.

        Args:
            json_data (str): The content of the JSON file in string format.
            other_config_data (dict): Other configuration data used for business logic validation.

        Raises:
            ValueError: If custom business logic validation fails.
        """
        # Common business logic across setting files
        pass

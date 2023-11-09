import json


class SettingsReader:
    """Represents a reader for settings stored in JSON format.

    This class provides functionality to read and access settings from a JSON file.

    Attributes:
        settings_file_name (str): Name of the settings file.
        settings (dict): Parsed settings data as a dictionary.

    Methods:
        parse_json: Parses the input JSON data into a Python dictionary.
        get_settings_file_name: Retrieves the name of the settings file.
        get_setting: Retrieves a specific setting by its name.

    Raises:
        JSONDecodeError: If there's an error parsing the JSON data.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        """SettingsReader class constructor.

        Args:
            settings_file_name (str): The name of the settings file.
            settings_data (str): The content of the settings file in JSON format.
        """
        self._settings_file_name = settings_file_name
        self.settings = self.parse_json(settings_data, settings_file_name)

    @property
    def settings_file_name(self) -> str:
        """Property to get the name of the settings file."""
        return self._settings_file_name

    def parse_json(self, settings_data: str, settings_file_name: str) -> dict:
        """Parses the input JSON data into a Python dictionary.

        Args:
            settings_data (str): The content of the settings file in JSON format.
            settings_file_name (str): The name of the settings file.

        Returns:
            dict: Parsed settings data as a dictionary.

        Raises:
            json.JSONDecodeError: If there's an error parsing the JSON data.

        """
        try:
            parsed_data = json.loads(settings_data)
            return parsed_data
        except json.decoder.JSONDecodeError as e:
            raise json.decoder.JSONDecodeError(
                f"Error parsing JSON file {settings_file_name}", e.doc, e.pos
            )

    def get_setting(self, setting_name: str):
        """Retrieves a specific setting by its name.

        Args:
            setting_name (str): The name of the setting to retrieve.

        Returns:
            Any: The value of the specified setting.

        """
        return self.settings.get(setting_name)

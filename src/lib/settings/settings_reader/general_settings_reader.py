from .settings_reader import SettingsReader


class GeneralSettingsReader(SettingsReader):
    """Represents a reader for General settings stored in JSON format.

    This class extends the SettingsReader to provide access to General settings from a JSON file.

    Attributes:
        tooling_environment (dict): Dictionary of the tooling environment.
        monitored_environments (dict): Dictionary of monitored environments.
        delivery_methods (dict): Dictionary of delivery methods.

    Methods:
        get_tooling_environment: Retrieves the tooling environment from the General settings.
        get_monitored_environments: Retrieves the monitored environments from the General settings.
        get_delivery_methods: Retrieves the delivery methods from the General settings.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        """GeneralSettingsReader class constructor.

        Args:
            settings_file_name (str): The name of the General settings file.
            settings_data (str): The content of the General settings file in JSON format.
        """
        super().__init__(settings_file_name, settings_data)
        self.tooling_environment = self.get_setting("tooling_environment")
        self.monitored_environments = self.get_setting("monitored_environments")
        self.delivery_methods = self.get_setting("delivery_methods")

    def get_tooling_environment(self) -> dict:
        """Retrieves the tooling environment from the General settings.

        Returns:
            dict: Dictionary of tooling environment.
        """
        return self.tooling_environment

    def get_monitored_environments(self) -> dict:
        """Retrieves the monitored environments from the General settings.

        Returns:
            dict: Dictionary of monitored environments.
        """
        return self.monitored_environments

    def get_delivery_methods(self) -> dict:
        """Retrieves the delivery methods from the General settings.

        Returns:
            dict: Dictionary of delivery methods.
        """
        return self.delivery_methods

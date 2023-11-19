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
        self._tooling_environment = self.get_setting("tooling_environment")
        self._monitored_environments = self.get_setting("monitored_environments")
        self._delivery_methods = self.get_setting("delivery_methods")

    @property
    def tooling_environment(self) -> dict:
        """Property to get the tooling environment."""
        return self._tooling_environment

    @property
    def monitored_environments(self) -> dict:
        """Property to get the monitored environment."""
        return self._monitored_environments

    @property
    def delivery_methods(self) -> dict:
        """Property to get the delivery methods."""
        return self._delivery_methods

    def get_monitored_environment_names(self) -> list[str]:
        """Retrieves the monitored_environment names from the General settings.

        Returns:
            list: List of monitored_environment names.
        """
        return [m_env.get("name") for m_env in self._monitored_environments]

    def get_delivery_method_names(self) -> list[str]:
        """Retrieves the delivery_method names from the General settings.

        Returns:
            list: List of delivery_method names.
        """
        return [dlvry_mthd.get("name") for dlvry_mthd in self._delivery_methods]

from .settings_reader import SettingsReader


class GeneralSettingsReader(SettingsReader):
    """Represents a reader for General settings stored in JSON format.

    This class extends the SettingsReader to provide access to General settings from a JSON file.

    Attributes:
        monitored_accounts (dict): Dictionary of monitored accounts.
        delivery_methods (dict): Dictionary of delivery methods.

    Methods:
        get_monitored_accounts: Retrieves the monitored accounts from the General settings.
        get_delivery_methods: Retrieves the delivery methods from the General settings.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        """GeneralSettingsReader class constructor.

        Args:
            settings_file_name (str): The name of the General settings file.
            settings_data (str): The content of the General settings file in JSON format.
        """
        super().__init__(settings_file_name, settings_data)
        self.monitored_accounts = self.get_setting("monitored_accounts")
        self.delivery_methods = self.get_setting("delivery_methods")

    def get_monitored_accounts(self) -> dict:
        """Retrieves the monitored accounts from the General settings.

        Returns:
            dict: Dictionary of monitored accounts.
        """
        return self.monitored_accounts

    def get_delivery_methods(self) -> dict:
        """Retrieves the delivery methods from the General settings.

        Returns:
            dict: Dictionary of delivery methods.
        """
        return self.delivery_methods

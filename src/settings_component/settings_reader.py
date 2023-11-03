import fnmatch
import json


class SettingsReader:
    """Represents a reader for settings stored in JSON format.

    This class provides functionality to read and access settings from a JSON file.

    Args:
        settings_file_name (str): The name of the settings file.
        settings_data (str): The content of the settings file in JSON format.

    Attributes:
        settings_file_name (str): Name of the settings file.
        settings (dict): Parsed settings data as a dictionary.

    Methods:
        parse_json: Parses the input JSON data into a Python dictionary.
        get_settings_file_name: Retrieves the name of the settings file.
        get_setting: Retrieves a specific setting by its name.

    Raises:
        json.JSONDecodeError: If there's an error parsing the JSON data.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        self.settings_file_name = settings_file_name
        self.settings = self.parse_json(settings_data, settings_file_name)

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
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Error parsing JSON file {settings_file_name} : {e}"
            )

    def get_settings_file_name(self) -> str:
        """Retrieves the name of the settings file.

        Returns:
            str: Name of the settings file.

        """
        return self.settings_file_name

    def get_setting(self, setting_name: str):
        """Retrieves a specific setting by its name.

        Args:
            setting_name (str): The name of the setting to retrieve.

        Returns:
            Any: The value of the specified setting.

        """
        return self.settings.get(setting_name)


class GeneralSettingsReader(SettingsReader):
    """Represents a reader for General settings stored in JSON format.

    This class extends the SettingsReader to provide access to General settings from a JSON file.

    Args:
        settings_file_name (str): The name of the General settings file.
        settings_data (str): The content of the General settings file in JSON format.

    Attributes:
        monitored_accounts (dict): Dictionary of monitored accounts.
        delivery_methods (dict): Dictionary of delivery methods.

    Methods:
        get_monitored_accounts: Retrieves the monitored accounts from the General settings.
        get_delivery_methods: Retrieves the delivery methods from the General settings.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
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


class MonitoringSettingsReader(SettingsReader):
    """Represents a reader for Monitoring settings stored in JSON format.

    This class extends the SettingsReader to provide access to Monitoring settings from a JSON file.

    Args:
        settings_file_name (str): The name of the Monitoring settings file.
        settings_data (str): The content of the Monitoring settings file in JSON format.

    Attributes:
        monitoring_groups (dict): Dictionary of monitoring groups.

    Methods:
        get_monitoring_groups: Retrieves the list of monitoring groups.
        get_monitoring_groups_by_resource_name: Retrieves monitoring groups based on resource name.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        super().__init__(settings_file_name, settings_data)
        self.monitoring_groups = self.get_setting("monitoring_groups")

    def get_monitoring_groups(self) -> dict:
        """Retrieves the monitoring groups from the Monitoring settings.

        Returns:
            dict: Dictionary of monitoring groups.
        """
        return self.monitoring_groups

    def get_monitoring_groups_by_resource_name(self, name: str) -> list[str]:
        """Retrieves monitoring groups based on resource name.

        Args:
            name (str): The resource name to match against monitoring groups.

        Returns:
            list[str] : List of matched monitoring group names.
        """
        matched_groups = []
        for group in self.monitoring_groups:
            glue_jobs = group.get("glue_jobs", [])
            lambda_functions = group.get("lambda_functions", [])

            for job in glue_jobs:
                job_name = job.get("name")
                if job_name and (job_name == name or "*" in job_name):
                    if fnmatch.fnmatch(
                        name, job_name
                    ):  # Checks that name matches the wildcard pattern
                        matched_groups.append(group.get("group_name"))

            for function in lambda_functions:
                function_name = function.get("name")
                if function_name and (function_name == name or "*" in function_name):
                    if fnmatch.fnmatch(
                        name, function_name
                    ):  # Checks that name matches the wildcard pattern
                        matched_groups.append(group.get("group_name"))

        return matched_groups


class RecipientsSettingsReader(SettingsReader):
    """Represents a reader for Recipients settings stored in JSON format.

    This class extends the SettingsReader to provide access to Recipients settings from a JSON file.

    Args:
        settings_file_name (str): The name of the Recipients settings file.
        settings_data (str): The content of the Recipients settings file in JSON format.

    Attributes:
        recipients (dict): Dictionary of recipient details.

    Methods:
        get_recipients: Retrieves the list of recipient details.
        get_recipients_by_monitoring_group_and_type: Retrieves recipients for a specific monitoring group and notification type.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        super().__init__(settings_file_name, settings_data)
        self.recipients = self.get_setting("recipients")

    def get_recipients(self) -> dict:
        """Retrieves the recipient details.

        Returns:
            dict: Dictionary of recipient details.
        """
        return self.recipients

    def get_recipients_by_monitoring_group_and_type(
        self, monitoring_group: str, notification_type: str
    ) -> list[dict]:
        """Retrieves recipients for a specific monitoring group and notification type.

        Args:
            monitoring_group (str): The name of the monitoring group.
            notification_type (str): The type of notification ('alert' or 'digest').

        Returns:
            list[dict] : List of recipient details for the specified monitoring group and notification type.
        """
        recipients_list = []
        for recipient in self.recipients:
            subscriptions = recipient.get("subscriptions", [])
            for subscription in subscriptions:
                if subscription.get("monitoring_group") == monitoring_group:
                    if (
                        notification_type == "alert" and subscription.get("alerts")
                    ) or (notification_type == "digest" and subscription.get("digest")):
                        recipient_info = {
                            "recipient": recipient.get("recipient"),
                            "delivery_method": recipient.get("delivery_method"),
                        }
                        recipients_list.append(recipient_info)

        return recipients_list

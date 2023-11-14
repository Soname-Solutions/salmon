from .settings_reader import SettingsReader


class RecipientsSettingsReader(SettingsReader):
    """Represents a reader for Recipients settings stored in JSON format.

    This class extends the SettingsReader to provide access to Recipients settings from a JSON file.

    Attributes:
        recipients (dict): Dictionary of recipient details.

    Methods:
        get_recipients: Retrieves the list of recipient details.
        get_recipients_by_monitoring_group_and_type: Retrieves recipients for a specific monitoring group and notification type.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        """RecipientsSettingsReader class constructor.

        Args:
            settings_file_name (str): The name of the Recipients settings file.
            settings_data (str): The content of the Recipients settings file in JSON format.
        """
        super().__init__(settings_file_name, settings_data)
        self.recipients = self.get_setting("recipients")

    def get_recipients(self) -> dict:
        """Retrieves the recipient details.

        Returns:
            dict: Dictionary of recipient details.
        """
        return self.recipients

    def get_recipients_by_monitoring_groups_and_type(
        self, monitoring_groups: list[str], notification_type: str
    ) -> list[dict]:
        """Retrieves recipients for the list of monitoring groups and notification type.

        Args:
            monitoring_groups (list[str]): Names of monitoring groups.
            notification_type (str): The type of notification ('alert' or 'digest').

        Returns:
            list[dict] : List of recipient details for the specified monitoring group and notification type.
        """
        matched_recipients = []

        for recipient in self.recipients:
            subscriptions = recipient.get("subscriptions", [])
            for subscription in subscriptions:
                for monitoring_group in monitoring_groups:
                    if subscription.get("monitoring_group") == monitoring_group:
                        if (
                            notification_type == "alert" and subscription.get("alerts")
                        ) or (
                            notification_type == "digest" and subscription.get("digest")
                        ):
                            recipient_info = {
                                "recipient": recipient.get("recipient"),
                                "delivery_method": recipient.get("delivery_method"),
                            }
                            if recipient_info not in matched_recipients:
                                matched_recipients.append(recipient_info)

        return matched_recipients

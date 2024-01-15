from ..core.constants import NotificationType
from ..settings import Settings


class DeliveryOptionsResolver:
    @staticmethod
    def get_delivery_options(settings: Settings, resource_name: str) -> list[dict]:
        """Returns delivery options section for the given resource name based on settings config.

        Args:
            settings (Settings): Settings component.
            resource_name (str): Name of the AWS resource.

        Returns:
            list[dict]: List of delivery options including recipient and delivery method
        """
        delivery_options = []
        recipients = {}
        monitoring_groups = settings.get_monitoring_groups([resource_name])
        recipients_settings = settings.get_recipients(
            monitoring_groups, NotificationType.ALERT
        )

        for recipient_setting in recipients_settings:
            delivery_method = recipient_setting["delivery_method"]
            recipient = recipient_setting["recipient"]

            if delivery_method not in recipients:
                recipients[delivery_method] = []

            recipients[delivery_method].append(recipient)

        for delivery_method, recipients_array in recipients.items():
            delivery_option = {
                "delivery_method": delivery_method,
                "recipients": recipients_array,
                "sender_email": settings.get_sender_email(delivery_method),
            }
            delivery_options.append(delivery_option)

        return delivery_options

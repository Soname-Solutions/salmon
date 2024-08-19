from ..core.constants import NotificationType
from ..settings import Settings


class DeliveryOptionsResolver:
    @staticmethod
    def get_delivery_options(
        settings: Settings, resource_type: str, resource_name: str
    ) -> list[dict]:
        """Returns delivery options section for the given resource name based on settings config.

        Args:
            settings (Settings): Settings component.
            resource_type (str): Resource type of the AWS resource.
            resource_name (str): Name of the AWS resource.

        Returns:
            list[dict]: List of delivery options including recipient and delivery method
        """
        delivery_options = []
        recipients = {}
        monitoring_groups = settings.get_monitoring_groups(
            resources=[resource_name], resource_type=resource_type
        )
        recipients_settings = settings.get_recipients(
            monitoring_groups, NotificationType.ALERT
        )

        for recipient_setting in recipients_settings:
            delivery_method_name = recipient_setting["delivery_method"]
            recipient = recipient_setting["recipient"]

            if delivery_method_name not in recipients:
                recipients[delivery_method_name] = []

            recipients[delivery_method_name].append(recipient)

        for delivery_method_name, recipients_array in recipients.items():
            delivery_option = {
                "delivery_method": settings.get_delivery_method(delivery_method_name),
                "recipients": recipients_array,
            }
            delivery_options.append(delivery_option)

        return delivery_options

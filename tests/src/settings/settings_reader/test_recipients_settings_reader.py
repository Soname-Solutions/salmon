import pytest
from src.settings.settings_reader import RecipientsSettingsReader


class TestRecipientsSettingsReader:
    @pytest.fixture(scope="class")
    def recipients_settings_data(self):
        return """
        {
            "recipients": [
                {
                    "recipient": "Recipient1",
                    "delivery_method": "Method1",
                    "subscriptions": [
                        {"monitoring_group": "Group1", "alerts": true, "digest": false},
                        {"monitoring_group": "Group2", "alerts": true, "digest": true}
                    ]
                },
                {
                    "recipient": "Recipient2",
                    "delivery_method": "Method2",
                    "subscriptions": [
                        {"monitoring_group": "Group2", "alerts": true, "digest": false}
                    ]
                },
                {
                    "recipient": "Recipient3",
                    "delivery_method": "Method3",
                    "subscriptions": [
                        {"monitoring_group": "Group3", "alerts": true, "digest": false}
                    ]
                }
            ]
        }
        """

    @pytest.fixture(scope="class")
    def recipients_data(self):
        return [
            {
                "recipient": "Recipient1",
                "delivery_method": "Method1",
                "subscriptions": [
                    {"monitoring_group": "Group1", "alerts": True, "digest": False},
                    {"monitoring_group": "Group2", "alerts": True, "digest": True},
                ],
            },
            {
                "recipient": "Recipient2",
                "delivery_method": "Method2",
                "subscriptions": [
                    {"monitoring_group": "Group2", "alerts": True, "digest": False}
                ],
            },
            {
                "recipient": "Recipient3",
                "delivery_method": "Method3",
                "subscriptions": [
                    {"monitoring_group": "Group3", "alerts": True, "digest": False}
                ],
            },
        ]

    @pytest.fixture(scope="class")
    def recipients_settings_reader(self, recipients_settings_data):
        return RecipientsSettingsReader("recipients.json", recipients_settings_data)

    def test_get_recipients(self, recipients_settings_reader, recipients_data):
        recipients = recipients_settings_reader.get_recipients()
        assert recipients == recipients_data

    def test_get_recipients_by_monitoring_groups_and_type(
        self, recipients_settings_reader
    ):
        monitoring_groups = ["Group1", "Group2"]
        alert_recipients = (
            recipients_settings_reader.get_recipients_by_monitoring_groups_and_type(
                monitoring_groups, "alert"
            )
        )
        assert alert_recipients == [
            {"recipient": "Recipient1", "delivery_method": "Method1"},
            {"recipient": "Recipient2", "delivery_method": "Method2"},
        ]

        digest_recipients = (
            recipients_settings_reader.get_recipients_by_monitoring_groups_and_type(
                monitoring_groups, "digest"
            )
        )
        assert digest_recipients == [
            {"recipient": "Recipient1", "delivery_method": "Method1"}
        ]

import pytest
import json
from src.settings.settings_reader import (
    SettingsReader,
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)
from json.decoder import JSONDecodeError


class TestSettingsReader:
    @pytest.fixture(scope="class")
    def valid_json_settings(self):
        return '{"key1": "value1", "key2": "value2"}'

    @pytest.fixture(scope="class")
    def invalid_json_settings(self):
        return "not a json"

    @pytest.fixture(scope="class")
    def settings_reader(self, valid_json_settings):
        return SettingsReader("test.json", valid_json_settings)

    def test_parse_json_valid(self, settings_reader, valid_json_settings):
        # Test parsing valid JSON data
        assert settings_reader.settings_file_name == "test.json"
        assert settings_reader.settings == json.loads(valid_json_settings)

    def test_parse_json_invalid(self, invalid_json_settings):
        # Test parsing invalid JSON data
        with pytest.raises(JSONDecodeError):
            SettingsReader("test.json", invalid_json_settings)

    def test_get_settings_file_name(self, settings_reader):
        # Test getting settings file name
        assert settings_reader.get_settings_file_name() == "test.json"

    def test_get_setting(self, settings_reader):
        # Test getting a specific setting by name
        assert settings_reader.get_setting("key1") == "value1"
        assert settings_reader.get_setting("key2") == "value2"
        assert settings_reader.get_setting("non_existent_key") is None


class TestGeneralSettingsReader:
    @pytest.fixture(scope="class")
    def general_settings_data(self):
        return """
        {
            "monitored_accounts": [{"name": "account1"}, {"name": "account2"}],
            "delivery_methods": [{"name": "method1"}, {"name": "method2"}]
        }
        """

    @pytest.fixture(scope="class")
    def general_settings_reader(self, general_settings_data):
        return GeneralSettingsReader("general.json", general_settings_data)

    def test_get_monitored_accounts(self, general_settings_reader):
        monitored_accounts = general_settings_reader.get_monitored_accounts()
        assert monitored_accounts == [{"name": "account1"}, {"name": "account2"}]

    def test_get_delivery_methods(self, general_settings_reader):
        delivery_methods = general_settings_reader.get_delivery_methods()
        assert delivery_methods == [{"name": "method1"}, {"name": "method2"}]


class TestMonitoringSettingsReader:
    @pytest.fixture(scope="class")
    def monitoring_settings_data(self):
        return """
        {
            "monitoring_groups": [
                {
                    "group_name": "Group1",
                    "glue_jobs": [{"name": "job1"}, {"name": "job2"}],
                    "lambda_functions": [{"name": "function1"}]
                },
                {
                    "group_name": "Group2",
                    "glue_jobs": [{"name": "job3"}, {"name": "job4"}],
                    "lambda_functions": [{"name": "function2"}]
                },
                {
                    "group_name": "Group1_intersected",
                    "glue_jobs": [{"name": "job5"}, {"name": "job6"}],
                    "lambda_functions": [{"name": "function2"}]
                },
                {
                    "group_name": "Group2_intersected",
                    "glue_jobs": [{"name": "job6"}, {"name": "job7"}],
                    "lambda_functions": [{"name": "function3"}]
                }
            ]
        }
        """

    @pytest.fixture(scope="class")
    def monitoring_groups_data(self):
        return [
            {
                "group_name": "Group1",
                "glue_jobs": [{"name": "job1"}, {"name": "job2"}],
                "lambda_functions": [{"name": "function1"}],
            },
            {
                "group_name": "Group2",
                "glue_jobs": [{"name": "job3"}, {"name": "job4"}],
                "lambda_functions": [{"name": "function2"}],
            },
            {
                "group_name": "Group1_intersected",
                "glue_jobs": [{"name": "job5"}, {"name": "job6"}],
                "lambda_functions": [{"name": "function2"}],
            },
            {
                "group_name": "Group2_intersected",
                "glue_jobs": [{"name": "job6"}, {"name": "job7"}],
                "lambda_functions": [{"name": "function3"}],
            },
        ]

    @pytest.fixture(scope="class")
    def monitoring_settings_reader(self, monitoring_settings_data):
        return MonitoringSettingsReader(
            "monitoring_groups.json", monitoring_settings_data
        )

    def test_get_monitoring_groups(
        self, monitoring_settings_reader, monitoring_groups_data
    ):
        monitoring_groups = monitoring_settings_reader.get_monitoring_groups()
        assert monitoring_groups == monitoring_groups_data

    def test_get_monitoring_groups_by_resource_names(self, monitoring_settings_reader):
        resources = ["job1", "function2"]
        matched_groups = (
            monitoring_settings_reader.get_monitoring_groups_by_resource_names(
                resources
            )
        )
        assert sorted(matched_groups) == ["Group1", "Group1_intersected", "Group2"]


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

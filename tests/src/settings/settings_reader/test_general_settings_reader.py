import pytest
from src.settings.settings_reader import GeneralSettingsReader


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

import pytest
from src.lib.settings.settings_reader import GeneralSettingsReader


class TestGeneralSettingsReader:
    @pytest.fixture(scope="class")
    def general_settings_data(self):
        return """
        {
            "tooling_environment": {"name": "account1"},
            "monitored_environments": [{"name": "account1"}, {"name": "account2"}],
            "delivery_methods": [{"name": "method1"}, {"name": "method2"}]
        }
        """

    @pytest.fixture(scope="class")
    def general_settings_reader(self, general_settings_data):
        return GeneralSettingsReader("general.json", general_settings_data)

    def test_get_tooling_environment(self, general_settings_reader):
        tooling_environment = general_settings_reader.get_tooling_environment()
        assert tooling_environment == {"name": "account1"}

    def test_get_monitored_environments(self, general_settings_reader):
        monitored_environments = general_settings_reader.get_monitored_environments()
        assert monitored_environments == [{"name": "account1"}, {"name": "account2"}]

    def test_get_delivery_methods(self, general_settings_reader):
        delivery_methods = general_settings_reader.get_delivery_methods()
        assert delivery_methods == [{"name": "method1"}, {"name": "method2"}]

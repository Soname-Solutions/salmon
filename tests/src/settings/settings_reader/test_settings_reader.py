import pytest
import json
from src.settings.settings_reader import SettingsReader
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
        with pytest.raises(JSONDecodeError) as exc_info:
            SettingsReader("test.json", invalid_json_settings)

        assert "Error parsing JSON file" in str(exc_info.value)

    def test_get_settings_file_name(self, settings_reader):
        # Test getting settings file name
        assert settings_reader.get_settings_file_name() == "test.json"

    def test_get_setting(self, settings_reader):
        # Test getting a specific setting by name
        assert settings_reader.get_setting("key1") == "value1"
        assert settings_reader.get_setting("key2") == "value2"
        assert settings_reader.get_setting("non_existent_key") is None

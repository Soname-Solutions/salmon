import os
import json

from lib.settings.cdk.settings_validator import validate, SettingsValidatorException

from lib.settings import Settings
import pytest

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

def test_validate_good_config():
    config_path = os.path.join(CURRENT_FOLDER, "../test_configs/config1/")
    settings = Settings.from_file_path(config_path)

    result = validate(settings)

def test_validate_bad_json():
    config_path = os.path.join(CURRENT_FOLDER, "../test_configs/config8_bad_json/")
    with pytest.raises(json.decoder.JSONDecodeError):
        settings = Settings.from_file_path(config_path)   
        result = validate(settings)   

def test_validate_bad_json_schema():
    config_path = os.path.join(CURRENT_FOLDER, "../test_configs/config9_bad_json_schema/")
    settings = Settings.from_file_path(config_path)

    with pytest.raises(SettingsValidatorException):
        result = validate(settings)         

def test_validate_bad_json_duplicate_env_names():
    config_path = os.path.join(CURRENT_FOLDER, "../test_configs/config10_bad_json_schema_dup_envs/")
    settings = Settings.from_file_path(config_path)

    with pytest.raises(SettingsValidatorException, match="Non-unique names"):
        result = validate(settings)                
    
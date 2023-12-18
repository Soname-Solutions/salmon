import os
import json

from lib.core import json_utils as ju
from lib.core.constants import NotificationType
from lib.settings.cdk.settings_validator import validate
from lib.settings import Settings


def test_settings_validation(settings):
    """Test settings_validator.validate function"""
    validate(settings)
    print("Settings validation passed")


if __name__ == "__main__":
    test_settings_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(test_settings_dir, "../config/settings/")
    settings = Settings.from_file_path(config_path)

    test_settings_validation(settings)

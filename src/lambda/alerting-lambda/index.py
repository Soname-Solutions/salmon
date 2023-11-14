import os
import json

from lib.settings_reader.general_settings_reader import GeneralSettingsReader
from lib.constants import SettingFileNames


def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    helloworld = generate_hello_world()
    return {"message": SettingFileNames.GENERAL_FILE_NAME}

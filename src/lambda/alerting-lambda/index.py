import os
import json

from ...lib import SettingFileNames


def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    helloworld = generate_hello_world()
    return {"message": SettingFileNames.GENERAL_FILE_NAME}


if __name__ == "__main__":
    event = {}
    context = {}
    lambda_handler(event=event, context=context)

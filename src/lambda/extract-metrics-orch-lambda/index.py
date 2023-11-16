import os
import json


def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    # it is triggered once in <x> minutes by eventbridge schedule rule

    # 1. ask settings for all "monitored_environments"

    # 2. iterates through "monitored_environments"
    # foreach - 2a. invokes (async) extract-metrics lambda (params = "monitored_environment" name)

    helloworld = generate_hello_world()
    return {"message": helloworld}

import os
import json

from lib.settings import Settings

def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    # it is triggered once in <x> minutes by eventbridge schedule rule
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]

    # 1. ask settings for all "monitoring_groups"
    settings = Settings.from_s3_path(settings_s3_path)
    
    monitoring_groups = settings.list_monitoring_groups()

    # 2. iterates through "monitoring_groups"
    for monitoring_group in monitoring_groups:
        print(f"Processing {monitoring_group}")

    # foreach - 2a. invokes (async) extract-metrics lambda (params = "monitored_environment" name)

    helloworld = generate_hello_world()
    return {"message": helloworld}

# for future reference
# lambda_client = boto3.client('lambda')

# lambda_name = "lambda-salmon-extract-metrics-devam"



# response = lambda_client.invoke(
#     FunctionName=lambda_name,
#     InvocationType='Event',
#     Payload=json.dumps({"account_id":"123", "service":"glue"})
# )


if __name__ == "__main__":
    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devam/settings/"
    lambda_handler(None, None)
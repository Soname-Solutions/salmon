import os
import json
import logging

from lib.settings import Settings
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_client = boto3.client('lambda')


def lambda_handler(event, context):
    # it is triggered once in <x> minutes by eventbridge schedule rule
    settings_s3_path = os.environ["SETTINGS_S3_PATH"]
    lambda_extract_metrics_name = os.environ["LAMBDA_EXTRACT_METRICS_NAME"]

    # 1. ask settings for all "monitoring_groups"
    settings = Settings.from_s3_path(settings_s3_path)
    
    monitoring_groups = settings.list_monitoring_groups()

    # 2. iterates through "monitoring_groups"
    for monitoring_group in monitoring_groups:
        logger.info(f"Processing {monitoring_group}")

        # foreach - 2a. invokes (async) extract-metrics lambda (params = "monitored_environment" name)        
        lambda_client.invoke(
            FunctionName=lambda_extract_metrics_name,
            InvocationType='Event',
            Payload=json.dumps({"monitoring_group" : monitoring_group})
        )
        logger.info(f"Invoked lambda {lambda_extract_metrics_name} for monitoring group: {monitoring_group}")


if __name__ == "__main__":
    handler = logging.StreamHandler()    
    logger.addHandler(handler) # so we see logged messages in console when debugging

    os.environ["SETTINGS_S3_PATH"] = "s3://s3-salmon-settings-devam/settings/"
    os.environ["LAMBDA_EXTRACT_METRICS_NAME"] = "lambda-salmon-extract-metrics-devam"
    
    lambda_handler(None, None)
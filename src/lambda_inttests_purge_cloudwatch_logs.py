import boto3
import json
import logging

from lib.aws.lambda_manager import LambdaManager
from lib.aws.cloudwatch_manager import CloudWatchManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    print("Received event: " + json.dumps(event))

    try:
        request_type = event["RequestType"]
        lambda_function_names = event["ResourceProperties"]["lambda_function_names"]
        if request_type == "Delete":
            lman = LambdaManager()
            cwman = CloudWatchManager()
            for lambda_function_name in lambda_function_names:
                log_group_name = lman.get_log_group(
                    lambda_function_name=lambda_function_name
                )
                log_group_exists = cwman.log_group_exists(log_group_name)
                if log_group_exists:
                    logger.info(f"Purging log streams for {lambda_function_name = }")
                    cwman.purge_log_streams(log_group_name=log_group_name)
                    logger.info(f"Done.")
                else:
                    logger.info(
                        f"Log group {log_group_name} doesn't exists. Skipping deletion of log streams."
                    )

        else:
            print(f"{request_type = }, skipping log purge")

    except Exception as e:
        print("Error: ", str(e))
        raise e  # Signal failure if an exception occurs

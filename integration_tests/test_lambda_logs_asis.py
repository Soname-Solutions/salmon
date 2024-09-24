import boto3
import random
import string
import zipfile
import io
import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from inttest_lib.common import get_stack_obj_for_naming
from inttest_lib.runners.lambda_function_runner import LambdaFunctionRunner
from lib.aws.aws_naming import AWSNaming


##################################################
def create_lambda_function(lambda_client, prefix) -> str:  # returns lambda name
    stack_for_naming = get_stack_obj_for_naming("amtst")
    iam_role_arn = "arn:aws:iam::658207859208:role/role-cttpavg-lambda-dev"

    # Generate a random 5-character string
    random_string = "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
    function_meaning = prefix + random_string
    function_name = AWSNaming.LambdaFunction(stack_for_naming, function_meaning)

    # Package the lambda code into a ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.writestr(
            "lambda_function.py",
            """
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("Successful lambda execution")
    
    message = "SUCCESS lambda greetings"
    logger.info(message)
    return {"message": message}
    """,
        )
    zip_buffer.seek(0)

    # Create the Lambda function
    response = lambda_client.create_function(
        FunctionName=function_name,
        Runtime="python3.11",
        Role=iam_role_arn,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_buffer.read()},
        Description=function_meaning,
        Timeout=30,
        MemorySize=128,
        Publish=True,
    )

    # wait till function is created (initially it's in PENDING)
    print("Waiting for the Lambda function to become Active...")
    while True:
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        state = response["State"]
        if state == "Active":
            print(f"Lambda function '{function_name}' is now Active.")
            break
        elif state == "Failed":
            print(f"Lambda function '{function_name}' creation failed.")
            break
        else:
            print(f"Function state: {state}. Waiting...")
            time.sleep(5)  # Wait for 5 seconds before checking again

    return function_name


##################################################
if __name__ == "__main__":
    lambda_client = boto3.client("lambda")
    function_name = create_lambda_function(lambda_client, prefix="asis")

    print(f"Lambda function '{function_name}' created successfully.")

    runner = LambdaFunctionRunner([function_name], "us-east-1")
    runner.initiate()

    runner.await_completion()

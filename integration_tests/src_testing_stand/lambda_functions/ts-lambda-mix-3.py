import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

failure_count = 0
last_request_id = None


def lambda_handler(event, context):
    current_request_id = context.aws_request_id

    global failure_count, last_request_id
    if last_request_id != current_request_id:
        # Reset failure count for the new request ID
        failure_count = 0
        last_request_id = current_request_id

    if failure_count == 0:
        logger.info("Started first unsuccessful lambda execution - ts-lambda-mix-3")
        failure_count += 1
        raise Exception("Intentional failure on first run - ts-lambda-mix-3")
    elif failure_count == 1:
        logger.info("Started second unsuccessful lambda execution - ts-lambda-mix-3")
        failure_count += 1
        raise Exception("Intentional failure on second run - ts-lambda-mix-3")
    else:
        logger.info("Started third successful lambda execution - ts-lambda-mix-3")
        return {
            "statusCode": 200,
            "body": "Lambda ts-lambda-mix-3 succeeded after retry!",
        }

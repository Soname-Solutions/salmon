import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

failure_count = 0


def lambda_handler(event, context):
    global failure_count
    if failure_count == 0:
        logger.info("Started first unsuccessful lambda execution - ts-lambda-mix-3")
        failure_count += 1
        raise Exception("Intentional failure on first run - ts-lambda-mix-3")
    else:
        logger.info("Started second successful lambda execution - ts-lambda-mix-3")
        return {
            "statusCode": 200,
            "body": "Lambda ts-lambda-mix-3 succeeded after retry!",
        }

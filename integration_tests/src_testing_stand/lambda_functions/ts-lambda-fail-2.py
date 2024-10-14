import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Started second fail lambda execution")
    logger.error("Logger: intentional failure - ts-lambda-fail-2")

    raise Exception("intentional failure - ts-lambda-fail-2")

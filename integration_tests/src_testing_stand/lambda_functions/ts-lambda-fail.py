import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Started fail lambda execution")

    raise Exception("intentional failure - ts-lambda-fail")
       

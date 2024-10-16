import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info("Successful lambda execution")

    message = "SUCCESS lambda greetings"
    logger.info(message)
    return {"message": message}

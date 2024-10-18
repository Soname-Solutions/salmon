import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

lambda_state = {"failure_count": 0, "last_request_id": None}


def lambda_handler(event, context):
    current_request_id = context.aws_request_id

    if lambda_state["last_request_id"] != current_request_id:
        # Reset failure count for the new request ID
        lambda_state["failure_count"] = 0
        lambda_state["last_request_id"] = current_request_id

    if lambda_state["failure_count"] == 0:
        logger.info("Started first unsuccessful lambda execution - ts-lambda-mix-3")
        lambda_state["failure_count"] += 1
        raise Exception("Intentional failure on first run - ts-lambda-mix-3")

    elif lambda_state["failure_count"] == 1:
        logger.info("Started second unsuccessful lambda execution - ts-lambda-mix-3")
        lambda_state["failure_count"] += 1
        raise Exception("Intentional failure on second run - ts-lambda-mix-3")

    else:
        logger.info("Started third successful lambda execution - ts-lambda-mix-3")
        return {
            "statusCode": 200,
            "body": "Lambda ts-lambda-mix-3 succeeded after retry!",
        }

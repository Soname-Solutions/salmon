import os
import json


def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):
    # it is triggered by extract-metrics-orch(estration) lambda
    # in param = monitored env name

    # 1. gets from settings component:
    # - monitored_env settings (including metrics extraction role arn - even if it's implicit - by default)
    # - relevant monitoring_groups with settings

    # 2. iterates through all entries in monitoring_groups (glue jobs, lambdas, step functions etc.)
    # inside the cycle:

    # 2-1. get last update time from timestream table (dims: monitored_env, service_name, entity_name)

    # 2-2. creates object of class <service>MetricsExtractor, runs it providing last_update_time (so, collect metrics since then)
    # component returns records to be written into TimeStream

    # 2-3. writes metrics into TimeStream table related to specific AWS service (glue/lambda etc.)

    # 2-x. updates "last update time" for this entity (if success. "last_update_time" = for step 2-2)

    helloworld = generate_hello_world()
    return {"message": helloworld}

import os
import json
import lib.settings.settings_reader

def generate_hello_world():
    return "Hello World!"


def lambda_handler(event, context):

    # 1. parses event to identify "source" - e.g. "glue"

    # 2. Create instance of <source>AlertParser class and calls method "parse"
    # parse method returns DSL-markedup message

    # 3. asks settings module for 
    # a) monitoring group item belongs to 
    # b) list of relevant recipients and their delivery method

    # 3. for each recipient:
    # sends message to SQS queue (DSL-markup + recipient and delivery method info)

    # 4. writes event into timestream DB table named <<TBD>>
    # dimensions: a) monitoring group, b) service
    # metric = error message

    helloworld = generate_hello_world()
    return {"message": helloworld}

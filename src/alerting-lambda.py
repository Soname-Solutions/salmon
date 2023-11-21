import os
import json
import boto3
import time
#import lib.settings.settings_reader
#from datetime import datetime

timestream_write_client = boto3.client('timestream-write')

def write_event_to_timestream(event):
    #################################################################
    db_name = "timestream-salmon-metrics-events-storage-devam"
    table_name = "alert-events"

    MONITORED_ENVIRONMENT = "test_env1"
    source = event.get("source","Source Unknown")
    #################################################################
    dimensions = [
        {'Name': 'Monitored_Environment', 'Value': MONITORED_ENVIRONMENT},
        {'Name': 'Source', 'Value': source}
    ]    
    record_time = str(int(round(time.time() * 1000)))

    records = []

    # JobRunState measure
    records.append({
        'Dimensions': dimensions,
        'MeasureName': 'EventJson',
        'MeasureValue': json.dumps(event, indent=4),
        'MeasureValueType': 'VARCHAR',
        'Time': record_time
    })

    result = timestream_write_client.write_records(DatabaseName=db_name, TableName=table_name, Records=records)

def lambda_handler(event, context):
    print(f"event = {event}")

    write_event_to_timestream(event)

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

    #helloworld = generate_hello_world()
    return {"event": event}

if __name__ == "__main__":
    event_raw = '{"version": "0", "id": "cc90c8c7-57a6-f950-2248-c4c8db98a5ef", "detail-type": "test_event", "source": "awssoname.test", "account": "405389362913", "time": "2023-11-21T13:31:35Z", "region": "eu-central-1", "resources": [], "detail": {"reason": "test"}}'
    event = json.loads(event_raw)
    context = None
    lambda_handler(event, context)

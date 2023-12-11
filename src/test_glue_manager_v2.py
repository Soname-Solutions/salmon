from datetime import datetime, timedelta

import boto3
import pytz

from lib.aws.glue_manager_v2 import GlueManager
from lib.aws.timestream_manager import TimestreamTableWriter

glue_client = boto3.client("glue")
timestream_client = boto3.client("timestream-write")

def prepare_records(glue_job_name, monitored_environment_name, job_runs):   
    common_dimensions = [{ "Name" : "monitored_environment", "Value" : monitored_environment_name },
                     { "Name" : "job_name", "Value" : glue_job_name }
                    ]

    common_attributes = {"Dimensions": common_dimensions}

    records = []
    for job_run in job_runs:
        dimensions = [{"Name" : "job_run_id", "Value" : job_run.Id}]

        metric_values = [
            ("execution", 1, "BIGINT"),
            ("succeeded", int(job_run.IsSuccess), "BIGINT"),
            ("failed", int(job_run.IsFailure), "BIGINT"),
            ("duration", job_run.ExecutionTime, "DOUBLE"),
        ]
        measure_values = [{"Name" : metric_name, "Value" : str(metric_value), "Type" : metric_type} for metric_name, metric_value, metric_type in metric_values]

        record_time = TimestreamTableWriter.datetime_to_epoch_milliseconds(job_run.StartedOn)

        records.append(
            {
                "Dimensions": dimensions,
                "MeasureName": 'job_execution',
                "MeasureValueType": 'MULTI',
                "MeasureValues": measure_values,
                "Time": record_time,
            }
        )

    return records, common_attributes

def get_latest_record_time(job_name):
    # query timestream table for latest record time (filter by job_name)
    # return latest record time
    timestream_query_client = boto3.client("timestream-query")
    query = f"""SELECT MAX(time) AS latest_record_time FROM {db_name}.{table_name} WHERE job_name = '{job_name}'
    """
    response = timestream_query_client.query(QueryString=query, MaxRows=1)
    print(response)


##########################################################################

##########################################################################
monitored_env0 = "test_monitored_env"
glue_job_name = "glue-salmonts-pyjob-one-dev"
since_time = datetime.now(tz=pytz.UTC) - timedelta(hours=5)
##########################################################################
db_name = "timestream-salmon-metrics-events-storage-devam"
table_name = "tstable-salmon-glue-metrics-devam"
##########################################################################

glue_man = GlueManager(glue_client)
timestream_man = TimestreamTableWriter(db_name=db_name, table_name=table_name, timestream_write_client=timestream_client)

# 1.
job_runs = glue_man.get_job_runs(glue_job_name, since_time=since_time)

# 2.
records, common_attributes = prepare_records(glue_job_name, monitored_env0, job_runs)

# 3.
response = timestream_man.write_records(records, common_attributes)

print(response)



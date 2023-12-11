from datetime import datetime, timedelta

import boto3
import pytz

from lib.aws.glue_manager import GlueManager
from lib.aws.timestream_manager import TimestreamTableWriter, TimeStreamQueryRunner
from lib.metrics_extractor.glue_metrics_extractor import GlueMetricExtractor

glue_client = boto3.client("glue")
timestream_client = boto3.client("timestream-write")
timestream_query_client = boto3.client("timestream-query")

##########################################################################
db_name = "timestream-salmon-metrics-events-storage-devam"
table_name = "tstable-salmon-glue-metrics-devam"
##########################################################################

#glue_man = GlueManager(glue_client)
timestream_man = TimestreamTableWriter(
    db_name=db_name, table_name=table_name, timestream_write_client=timestream_client
)

monitored_env0 = "test_monitored_env"
glue_job_names = ["glue-salmonts-pyjob-one-dev", "glue-salmonts-sparkjob-one-dev"]

for glue_job_name in glue_job_names:
    print(f"Processing glue job {glue_job_name}")

    # 1. Create an extractor object for a specific service
    glue_extractor = GlueMetricExtractor(
        glue_client=glue_client,
        glue_job_name=glue_job_name,
        monitored_environment_name=monitored_env0,
        timestream_db_name=db_name,
        timestream_metrics_table_name=table_name,
    )

    # 2. Get time of this entity's data latest update (we append data since that time only)
    since_time = glue_extractor.get_last_update_time(timestream_query_client = timestream_query_client)
    if since_time is None:
        since_time = timestream_man.get_earliest_writeable_time_for_table()    
    print(f"Extracting metrics since {since_time}")    

    # # 3. Extract metrics data in form of prepared list of timestream records
    records, common_attributes = glue_extractor.prepare_metrics_data(since_time=since_time)
    print(f"Extracted {len(records)} records")

    # # 4. Write extracted data to timestream table
    glue_extractor.write_metrics(records, common_attributes, timestream_table_writer=timestream_man)
    print(f"Written {len(records)} records to timestream")



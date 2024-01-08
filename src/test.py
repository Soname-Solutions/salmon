import boto3
import json

from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.core.constants import SettingConfigs
from lib.aws.aws_naming import AWSNaming

timestream_db_name = "timestream-salmon-metrics-events-storage-devam"
timestream_metrics_table_name = "tstable-glue_jobs-metrics"

for resource_type in SettingConfigs.RESOURCE_TYPES:
    print(resource_type)
    table_name = AWSNaming.TimestreamTable(None,resource_type)
    print(table_name)



# timestream_query_client=boto3.client('timestream-query')
# runner = TimeStreamQueryRunner(timestream_query_client)

# query = f'SELECT job_name, max(time) as max_time FROM "{timestream_db_name}"."{timestream_metrics_table_name}" GROUP BY job_name'
# print(query)

# result = runner.execute_query(query)
# print(json.dumps(result, indent=2))

# print(type(result[1]['max_time']))

# # column_names = [x.Name for x in result.ColumnInfo]

# # result_rows = []
# # for row in result.Rows:
# #     values = [x.ScalarValue for x in row.Data]
# #     data_row = dict(zip(column_names, values))   
# #     result_rows.append(data_row)



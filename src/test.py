from lib.settings import Settings
from lib.aws.glue_manager import GlueManager



# settings = Settings.from_file_path("config/settings", iam_role_list_monitored_res="role-salmon-monitored-acc-extract-metrics-devam")

# # monitoring_group_name = "salmonts_pyjobs"
# # content = settings.get_monitoring_group_content(monitoring_group_name)

# # print(content)

# res = settings._get_all_resource_names()
# print(res)

import boto3

glue_client = boto3.client("glue")
mg = GlueManager(glue_client=glue_client)

names = mg.get()

print(names)
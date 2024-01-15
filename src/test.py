import json
from lib.settings import Settings

iam_role = "role-salmon-monitored-acc-extract-metrics-devam"

settings = Settings.from_file_path("../config/settings/", iam_role)

gr = settings.get_monitoring_group_content("salmonts_glue_all_group")

gr_str = json.dumps(gr, indent=4)
print(gr_str)
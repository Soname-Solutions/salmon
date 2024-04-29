from lib.settings import Settings

settings = Settings.from_file_path("config/settings", iam_role_list_monitored_res="role-salmon-monitored-acc-extract-metrics-devam")

monitoring_group_name = "salmonts_pyjobs"
content = settings.get_monitoring_group_content(monitoring_group_name)

print(content)
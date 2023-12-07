from lib.settings import Settings

from pydantic import BaseModel, Field
from typing import List, Optional

########################


class ToolingEnvironment(BaseModel):
    name: str
    account_id: str
    region: str
    metrics_collection_interval_min: int


class MonitoredEnvironment(BaseModel):
    name: str
    account_id: str
    region: str
    metrics_extractor_role_arn: str


class DeliveryMethod(BaseModel):
    name: str
    delivery_method_type: str
    sender_email: Optional[str] = None
    credentials_secret_name: Optional[str] = None


class GeneralConfig(BaseModel):
    tooling_environment: ToolingEnvironment
    monitored_environments: List[MonitoredEnvironment]
    delivery_methods: List[DeliveryMethod]


#########################


class GlueJob(BaseModel):
    name: str
    monitored_environment_name: str
    sla_seconds: int
    minimum_number_of_runs: int


class GlueWorkflow(BaseModel):
    name: str
    monitored_environment_name: str
    sla_seconds: int
    minimum_number_of_runs: int


class LambdaFunction(BaseModel):
    name: str
    monitored_environment_name: str
    minimum_number_of_runs: int
    sla_seconds: int


class StepFunction(BaseModel):
    name: str
    monitored_environment_name: str
    sla_seconds: int
    minimum_number_of_runs: int


class MonitoringGroup(BaseModel):
    group_name: str
    glue_jobs: Optional[List[GlueJob]] = None
    glue_workflows: Optional[List[GlueWorkflow]] = None
    lambda_functions: Optional[List[LambdaFunction]] = None
    step_functions: Optional[List[StepFunction]] = None


class MonitoringGroupsConfig(BaseModel):
    monitoring_groups: List[MonitoringGroup]


#########################


class Subscription(BaseModel):
    monitoring_group: str
    alerts: bool
    digest: bool


class Recipient(BaseModel):
    recipient: str
    delivery_method: str
    subscriptions: List[Subscription]


class RecipientsConfig(BaseModel):
    recipients: List[Recipient]


#########################


class Config(BaseModel):
    general_json: GeneralConfig = Field(..., alias="general.json")
    monitoring_groups_json: MonitoringGroupsConfig = Field(
        ..., alias="monitoring_groups.json"
    )
    recipients_json: RecipientsConfig = Field(..., alias="recipients.json")


#########################

settings = Settings.from_file_path("../config/settings/")

json_data = settings.processed_settings

pydantic_settings = Config.model_validate(json_data)

#1
print(f"Tooling env : {pydantic_settings.general_json.tooling_environment}")

#2
for mon_env in pydantic_settings.general_json.monitored_environments:
    print(f"Monitored env : {mon_env}")

#3
monitoring_group = "salmonts_pyjobs"
# only for subscriptions where alerts=True
relevant_recipients = [
    (r.delivery_method, r.recipient)
    for r in pydantic_settings.recipients_json.recipients
    if monitoring_group in [s.monitoring_group for s in r.subscriptions if s.alerts ]
]

print(relevant_recipients)


# + SHOW a case when sender_email is mandatory

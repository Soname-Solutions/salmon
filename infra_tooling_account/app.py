#!/usr/bin/env python3
import os
import sys
import logging

import aws_cdk as cdk
from aws_cdk import Aws
import boto3

sys.path.append("../src")
from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack
from infra_tooling_account.infra_tooling_alerting_stack import InfraToolingAlertingStack
from infra_tooling_account.infra_tooling_monitoring_stack import (
    InfraToolingMonitoringStack,
)
from infra_tooling_account.infra_tooling_grafana_stack import InfraToolingGrafanaStack

from lib.settings.settings import Settings
from lib.settings.cdk import settings_validator


logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENV_NAME = "tooling_environment"

settings = Settings.from_file_path("../config/settings")
settings_validator.validate(settings)

current_account = os.getenv("CDK_DEFAULT_ACCOUNT")
current_region = os.getenv("CDK_DEFAULT_REGION")
logging.info(
    f"Target AWS account: {current_account} and AWS Region: {current_region} determined by the AWS CDK"
)

tooling_account_id, tooling_region = settings.get_tooling_account_props()
env = {
    "region": tooling_region,
    "account": tooling_account_id,
}
settings_validator.validate_cdk_env_variables(
    env_name=ENV_NAME,
    cdk_env_variables={(current_account, current_region)},
    config_values={(tooling_account_id, tooling_region)},
)

app = cdk.App()

STAGE_NAME = app.node.try_get_context("stage-name")
if STAGE_NAME is None:
    raise KeyError("stage-name context variable is not set.")

logging.info(f"stage-name: {STAGE_NAME}")
PROJECT_NAME = "salmon"

TAGS = {"project_name": PROJECT_NAME, "stage_name": STAGE_NAME}

common_stack = InfraToolingCommonStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingCommonStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
    env=env,
)
alerting_stack = InfraToolingAlertingStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingAlertingStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
    env=env,
)
monitoring_stack = InfraToolingMonitoringStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingMonitoringStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
    env=env,
)

alerting_stack.add_dependency(common_stack)
monitoring_stack.add_dependency(common_stack)

if settings.get_grafana_settings():
    grafana_stack = InfraToolingGrafanaStack(
        app,
        f"cf-{PROJECT_NAME}-InfraToolingGrafanaStack-{STAGE_NAME}",
        tags=TAGS,
        stage_name=STAGE_NAME,
        project_name=PROJECT_NAME,
        settings=settings,
        env=env,
    )
    grafana_stack.add_dependency(common_stack)

app.synth()

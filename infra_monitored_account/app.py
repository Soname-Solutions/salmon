#!/usr/bin/env python3
import os
import sys
import logging

import aws_cdk as cdk

sys.path.append("../src")
from infra_monitored_account.infra_monitored_stack import InfraMonitoredStack

from lib.settings import Settings
from lib.settings.cdk import settings_validator

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ENV_NAME = "monitored_environment"

settings = Settings.from_file_path("../config/settings")
settings_validator.validate(settings)

current_account = os.getenv("CDK_DEFAULT_ACCOUNT")
current_region = os.getenv("CDK_DEFAULT_REGION")
logging.info(
    f"Target AWS account: {current_account} and AWS Region: {current_region} determined by the AWS CDK"
)

settings_validator.validate_cdk_env_variables(
    env_name=ENV_NAME,
    cdk_env_variables={(current_account, current_region)},
    config_values=settings.get_monitored_account_region_pairs(),
)

app = cdk.App()

STAGE_NAME = app.node.try_get_context("stage-name")
if STAGE_NAME is None:
    raise KeyError("stage-name context variable is not set.")

logging.info(f"stage-name: {STAGE_NAME}")
PROJECT_NAME = "salmon"

TAGS = {"project_name": PROJECT_NAME, "stage_name": STAGE_NAME}

InfraMonitoredStack(
    app,
    f"cf-{PROJECT_NAME}-InfraMonitoredStack-{STAGE_NAME}",
    tags={"project_name": PROJECT_NAME, "stage_name": STAGE_NAME},
    project_name=PROJECT_NAME,
    stage_name=STAGE_NAME,
    settings=settings,
)

app.synth()

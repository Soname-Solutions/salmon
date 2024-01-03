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

settings = Settings.from_file_path("../config/settings")
settings_validator.validate(settings)

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

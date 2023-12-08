#!/usr/bin/env python3
import os
import sys

import aws_cdk as cdk

sys.path.append("../src")
from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack
from infra_tooling_account.infra_tooling_alerting_stack import InfraToolingAlertingStack
from infra_tooling_account.infra_tooling_monitoring_stack import (
    InfraToolingMonitoringStack,
)

from lib.settings.settings import Settings
from lib.settings.cdk import settings_validator


if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
STAGE_NAME = os.environ["STAGE_NAME"]

PROJECT_NAME = "salmon"

TAGS = {"project_name": PROJECT_NAME, "stage_name": STAGE_NAME}

settings = Settings.from_file_path("../config/settings")
settings_validator.validate(settings)


app = cdk.App()
common_stack = InfraToolingCommonStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingCommonStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
)
alerting_stack = InfraToolingAlertingStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingAlertingStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
)
monitoring_stack = InfraToolingMonitoringStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingMonitoringStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    settings=settings,
)

alerting_stack.add_dependency(common_stack)
monitoring_stack.add_dependency(common_stack)

app.synth()

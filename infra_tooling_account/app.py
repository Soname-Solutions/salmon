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

from lib.settings.cdk.local_file_system_settings_provider import (
    LocalFileSystemSettingsProvider,
)


if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
STAGE_NAME = os.environ["STAGE_NAME"]

PROJECT_NAME = "salmon"

TAGS = {"project_name": PROJECT_NAME, "stage_name": STAGE_NAME}

settings_provider = LocalFileSystemSettingsProvider("../config/settings")
settings_provider.validate_settings()

app = cdk.App()
common_stack = InfraToolingCommonStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingCommonStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
)
alerting_stack = InfraToolingAlertingStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingAlertingStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    general_settings_reader=settings_provider.general_settings_reader,
)
monitoring_stack = InfraToolingMonitoringStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingMonitoringStack-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
    general_settings_reader=settings_provider.general_settings_reader,
)

alerting_stack.add_dependency(common_stack)
monitoring_stack.add_dependency(common_stack)

app.synth()

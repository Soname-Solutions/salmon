#!/usr/bin/env python3
import os
import sys

import aws_cdk as cdk

sys.path.append("../src")
from infra_monitored_account.infra_monitored_stack import InfraMonitoredStack

from lib.settings.cdk.local_file_system_settings_provider import (
    LocalFileSystemSettingsProvider,
)


if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
STAGE_NAME = os.environ["STAGE_NAME"]

PROJECT_NAME = "salmon"

settings_provider = LocalFileSystemSettingsProvider("../config/settings")
settings_provider.validate_settings()

app = cdk.App()
InfraMonitoredStack(
    app,
    f"cf-{PROJECT_NAME}-InfraMonitoredStack-{STAGE_NAME}",
    tags={"project_name": PROJECT_NAME, "stage_name": STAGE_NAME},
    project_name=PROJECT_NAME,
    stage_name=STAGE_NAME,
    general_settings_reader=settings_provider.general_settings_reader,
)

app.synth()

#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack
from infra_tooling_account.infra_tooling_alerting_stack import InfraToolingAlertingStack

if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
STAGE_NAME = os.environ["STAGE_NAME"]

PROJECT_NAME = "salmon"

app = cdk.App()
InfraToolingCommonStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingCommonStack-{STAGE_NAME}",
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
)
InfraToolingAlertingStack(
    app,
    f"cf-{PROJECT_NAME}-InfraToolingAlertingStack-{STAGE_NAME}",
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
)

app.synth()

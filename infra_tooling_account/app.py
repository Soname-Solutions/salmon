#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack
from infra_tooling_account.infra_tooling_alerting_stack import InfraToolingAlertingStack

if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
stage_name = os.environ["STAGE_NAME"]

project_name = "salmon"

app = cdk.App()
InfraToolingCommonStack(app, f"cf-{project_name}-InfraToolingCommonStack-{stage_name}", stage_name=stage_name, project_name=project_name)
InfraToolingAlertingStack(app, f"cf-{project_name}-InfraToolingAlertingStack-{stage_name}", stage_name=stage_name, project_name=project_name)

app.synth()

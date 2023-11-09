#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra_monitored_account.infra_monitored_stack import InfraMonitoredStack

if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
stage_name = os.environ["STAGE_NAME"]

project_name = "salmon"

app = cdk.App()
InfraMonitoredStack(app, f"cf-{project_name}-InfraMonitoredStack-{stage_name}", project_name=project_name, stage_name=stage_name)

app.synth()

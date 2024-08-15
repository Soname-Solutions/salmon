#!/usr/bin/env python3
import os
import sys
import logging

import aws_cdk as cdk

sys.path.append("../../src")
sys.path.append("../../integration_tests")

from stacks.testing_stand_stack import TestingStandStack

app = cdk.App()

STAGE_NAME = app.node.try_get_context("stage-name")
if STAGE_NAME is None:
    raise KeyError("stage-name context variable is not set.")

logging.info(f"stage-name: {STAGE_NAME}")
PROJECT_NAME = "salmon"

TAGS = {"project_name": PROJECT_NAME, "stage_name": STAGE_NAME}

main_stack = TestingStandStack(
    app,
    f"cf-{PROJECT_NAME}-TestingStand-{STAGE_NAME}",
    tags=TAGS,
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,
)

app.synth()

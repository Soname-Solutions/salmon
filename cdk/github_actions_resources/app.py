#!/usr/bin/env python3
import os
import sys
import logging

import aws_cdk as cdk

from stacks.github_actions_resources_stack import GitHubActionsResourcesStack

app = cdk.App()

PROJECT_NAME = "salmon"
STAGE_NAME = "all" # resources are shared among all salmon environments 

main_stack = GitHubActionsResourcesStack(
    app,
    f"cf-{PROJECT_NAME}-GithubActionsResources-{STAGE_NAME}",
)

app.synth()

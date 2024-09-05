#!/usr/bin/env python3
import sys

import aws_cdk as cdk

sys.path.append("../../src")

from stacks.github_actions_resources_stack import GitHubActionsResourcesStack

app = cdk.App()

PROJECT_NAME = "salmon"
STAGE_NAME = "all" # resources are shared among all salmon environments 

main_stack = GitHubActionsResourcesStack(
    app,
    f"cf-{PROJECT_NAME}-GithubActionsResources-{STAGE_NAME}",
    stage_name=STAGE_NAME,
    project_name=PROJECT_NAME,    
)

app.synth()

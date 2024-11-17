# CDK components

## Overview

This folder contains CDK applications and related resources for deploying and managing the **SALMON** project. It includes both core components for production environments and optional components for customization and testing.

**Core SALMON components:**

1. `tooling_environment` - CDK application to deploy the tooling environment.
2. `monitoring_environment` - CDK application to deploy the monitored environment.

**Optional component** (CDK customization):

1. `salmon_cdk_cloudformation_exec_policy.yaml` - CloudFormation template to create a custom policy for CDK deployments. This policy is less privileged than the default AdministratorAccess and contains only the permissions sufficient for deploying SALMON.

    For details, refer to [Limiting AWS CDK permissions](/docs/limit_cdk_permissions.md)

**Optional components** (integration / deployment tests):  

The following components are required if you are contributing to the SALMON project and need to execute integration or deployment tests before creating a pull request:

1. `github_actions_resources` - resources needed to run GitHub Actions workflows (e.g., IAM service role).
2. `integration_testing_stand`: testing stand and AWS resources required for executing tests.

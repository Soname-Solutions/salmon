# CDK components

## This Folder Content

This folder contains subfolders with CDK application:

**Core SALMON components:**

1. `tooling_environment` - CDK app to deploy tooling environment.
2. `monitoring_environment` - CDK app to deploy monitored environment.

**Optional component** (CDK customization):

1. `salmon_cdk_cloudformation_exec_policy.yaml` - CloudFormation template to create custom policy for CDK deployments (less-privileged than the default one, containing minimum sufficient permission for SALMON).

Please see section below for details.

**Optional components** (integration / deployment tests):  

The following components are required if you are a contributor to SALMON project and you want to execute integration/deployment tests before creating a Pull Request.

1. `github_actions_resources` - resources needed to run GitHub actions workflows (namely, IAM service role).
2. `integration_testing_stand`: testing stand + AWS resources required for tests execution.

## Limiting CDK execution role privileges

<<todo>>

```bash
aws cloudformation deploy --template-file salmon_cdk_cloudformation_exec_policy.yaml --stack-name cf-salmon-cdk-cloudformation-exec-policy-all --capabilities CAPABILITY_NAMED_IAM
```
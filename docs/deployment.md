# SALMON Deployment Guide

This article describes the installation and deployment for SALMON project.

![Deployment Workflow](/docs/images/deployment-workflow.svg "Deployment Workflow")

## Prerequisites

### Local Environment Setup

Make sure the following software is installed on your system:
- NodeJS
- AWS CDK Toolkit. You can refer to [AWS Guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for installation.
- AWS CLIv2. It's also recommended to set up AWS CLI profiles for AWS accounts where you tooling and monitored environments reside.
- Python environment with installed packages from (/requirements.txt) and, (optional) if you intend to run unit tests and integration tests locally (/requirements-test.txt)

### AWS Accounts Setup

#### CDK Bootstrap

Your Salmon installation will include one centralized (tooling) environment and, potentially, multiple monitored environments across different AWS accounts and regions (for more details on terminology, see [Key Concepts](/docs/key_concepts.md)).

Make sure AWS CDK bootstrap resources are created for each relevant AWS Account and region. For more information - refer to refer to [CDK Bootstrapping - AWS Documentation](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html).

#### Setting Up Notifications Delivery

Salmon can send notifications or messages (e.g. on Glue Job failure or Daily EMail digest).
The primary delivery method for the current version is AWS SES (with plans to add more options such as SMTP, Slack and MS Teams channel notifications).

For AWS SES make sure:
- The email address you intend use as "From" in SALMON notifications is added to AWS SES and verified.  
  "From" e-mail is configured in **'general.json'** - [see "Settings" documentation](/docs/configuration.md).
- All recipient email addresses (from **'recipients.json'**) are also verified in AWS SES identity.

It's a good practice (although not required) to create a separate email address to feature as Salmon notifications sender (
e.g. salmon-notifications@your-company.com).  
Among other benefits, this makes it easier to set up message filters in your email client.  

All emails should be added to AWS SES in the account/region where the tooling environment resides.

![AWS SES Configuration](/docs/images/ses-identities.png "AWS SES Configuration")

## Preparing SALMON settings

You need to prepare configuration files for the solution and place them in the **/config/** folder.  

For more details on Configuration, see [Documentation](/docs/configuration.md).

You can also refer to sample settings files in **/config/sample_settings/**.  

## CDK Deploy: Tooling Environment

Once all prerequisites are met and the configuration is ready, it's time to deploy all artifacts to AWS.
Deployment starts with the Tooling Environment:

- browse into **cdk/tooling_environment** folder
- run the following command  
```cdk deploy --context stage-name=<your_stage_name>```

Optionally, you can add an AWS profile identifier via the '--profile' command argument.

*`stage-name` is a parameter which identifies the deployment stage (usually dev/test/qa/uat/prod, but can be any string identifier of your choice).*

What happens during *`cdk deploy`* of tooling environment:
- Configuration files are validated (e.g. if delivery methods referred to in *recipients.json* are aligned with those defined in *general.json*)
- Configuration files are copied to S3 bucket (where all SALMON components will read the configuration from).
- AWS resources are created. For a list of resources, please refer to [Architecture document](/docs/architecture.md).

*Note: If you change the settings (e.g. add a new recipient), you will need to run the aforementioned "cdk deploy" command to validate new config files and upload them onto S3.*

*Note: If you choose to use optional Grafana component, make sure you to have a VPC with a public subnet and a security group prepared. The security group should allow access to port 3000 from any IP address.*

## CDK Deploy: Monitoring Environments

For each monitored environment you plan to control, you'll need to deploy resources into the respective AWS account and region with the following steps:
- browse into **cdk/monitored_environment** folder
- make sure you are using AWS credentials which have sufficient access to target AWS account
- execute the command  
```cdk deploy --context stage-name=<your_stage_name>```

*Note: use the same `stage-name` as chosen for the tooling environment*

Optionally, you can add an AWS profile identifier via --profile command argument.

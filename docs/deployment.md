# SALMON Deployment Guide

This article describes the installation and deployment for SALMON project.

![Deployment Workflow](/docs/images/deployment-workflow.svg "Deployment Workflow")

## Prerequisites

### Local Environment Setup

Make sure the following pieces of software are installed in your system:
- NodeJS
- AWS CDK Toolkit. You can refer to [AWS Guide](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) for installation.
- AWS CLIv2. It's also recommended AWS CLI profiles for AWS accounts where you tooling and monitored environments reside.
- Python environment with installed packages from (/infra_monitored_account/requirements.txt) and (/infra_tooling_account/requirements.txt)

### AWS Accounts Setup

#### CDK Bootstrap

Your Salmon installation will have one centralized (tooling) environment and, potentially, multiple monitored environments in different AWS accounts and regions (for more details on terminology - see [Key Concepts](/docs/key_concepts.md)).

Make sure CDK resources are created for each relevant AWS Account and region. For more information - refer to refer to [CDK Bootstrapping - AWS Documentation](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html).

#### Setting Up Notifications Delivery

Salmon can send notifications or messages (e.g. on Glue Job failure or Daily EMail digest).
Primary delivery method for current version is AWS SES (while there are plans to add more options such as SMTP, Slack and MS Teams channel notifications).

For AWS SES make sure:
- E-mail address you intend use as "From" in Salmon notifications is added to AWS SES and verified.  
  "From" e-mail is configured in general.json - [see "Settings" documentation](/docs/configuration.md).
- All recipients email address (from recipients.json) should also be verified in AWS SES identity.

It's a good practice (although not required) to create a separate e-mail address to feature as Salmon notifications sender (
e.g. salmon-notifications@your-company.com).  
Among other benefits, it'll make it easier to set up message filters in your email client.  

All e-mails should be added into AWS SES into account/region where tooling environment resides.

![AWS SES Configuration](/docs/images/ses-identities.png "AWS SES Configuration")

### Preparing SALMON settings

You need to prepare configuration files for the solution and place them under /config/ folder.  

For more details on Configuration - see [Documentation](/docs/configuration.md).

You can also refer to sample settings files in /config/sample_settings/.  

### CDK Deploy: Tooling Environment


### CDK Deploy: Monitoring Environments



# Old Content - check what to re-use

### Configuration Files

- You can refer to examples in /config/sample_settings/


## Tooling Environment Setup

- It can be either a separate AWS Account or one of the monitored AWS Accounts.
- Optional Grafana toolset can be included into deployment via Configuration parameters. See [Configuration Documentation](./configuration.md)
- stage-name parameter needs to be defined for deployment as an identifier of deployment stage (usually dev/test/qa/uat/prod, but can be any string identifier)

Assuming that your target AWS profile is the default one set, execute the following from /infra_tooling_account/ :

```cdk deploy --all --context stage-name=<your_stage_name>```

Optionally you can add an AWS profile identifier via --profile command argument.

## Monitored Environment Setup

- Monitored Environment is any combination of AWS Account and Region which needs to be monitored.
- Even if one of AWS Account and Region has Tooling stack configured, it still needs Monitored Environment deployment if you need to monitor services residing within this Account and Region
- stage-name parameter needs to be defined for deployment as an identifier of deployment stage (usually dev/test/qa/uat/prod, but can be any string identifier)

Assuming that your target AWS profile is the default one set, execute the following from /infra_monitored_account/ :

```cdk deploy --all --context stage-name=<your_stage_name>```

Optionally you can add an AWS profile identifier via --profile command argument.
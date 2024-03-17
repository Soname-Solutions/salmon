# SALMON Deployment Guide

This article describes the deployment instruction for SALMON project.

## Prerequisites

### Local Env Setup

- AWS CLIv2 with configured profiles for your target AWS Accounts 
- Python environment with installed packages from (/infra_monitored_account/requirements.txt) and (/infra_tooling_account/requirements.txt)
- NodeJS
- CDK Toolkit

### AWS Accounts Setup

- CDK Bootstrapping: for all monitored accounts and for the tooling account - refer to [AWS Documentation](https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html)
- (Optional) Create a custom IAM role to execute CDK deploments with (TODO: provide example?)

### Email Delivery

- If you are using AWS SES for email notifications - make sure email addresses you specify in recipients.json are verified in SES
- If you are using an SMTP server, you need to have a Secret in AWS Secrets Manager:
    - Secret name: your choice, the name should be referenced in general.json
    - Secret value: JSON of the following structure:
    {
        "SMTP_HOST": <your_smtp_server_host>,
        "SMTP_PORT": <your_smtp_server_port>,
        "SMTP_LOGIN": <your_smtp_server_username>,
        "SMTP_PASSWORD": <your_smtp_server_password>
    }

### Configuration Files

You need to prepare configuration files for the solution and place them under /config/ folder.

- You can refer to examples in /config/sample_settings/
- Or you can refer to [Configuration Documentation](./configuration.md)

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
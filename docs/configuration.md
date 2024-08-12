# SALMON Configuration

- [SALMON Configuration](#salmon-configuration)
  - [Overview ](#overview-)
      - [Quick Start ](#quick-start-)
      - [Configuration Structure ](#configuration-structure-)
  - [Configuration Steps](#configuration-steps)
    - [1. Create Configuration Files ](#1-create-configuration-files-)
    - [2. Configure General Settings  ](#2-configure-general-settings--)
    - [3. Configure Monitoring Groups  ](#3-configure-monitoring-groups--)
    - [4. Configure Recipients and Subscriptions  ](#4-configure-recipients-and-subscriptions--)
    - [5. \[Optional\] Configure Replacements for Placeholders ](#5-optional-configure-replacements-for-placeholders-)


## Overview <a name="overview"></a>
This guide provides instructions on how to configure the SALMON project to suit your monitoring and alerting needs. 

#### Quick Start <a name="quick-start"></a>

Before the deployment:
* **Prepare Configuration Files**: Sample configurations serving as templates are located at the `/config/sample_settings` directory. Copy these templates to the `/config/settings` directory if necessary and fill in the required values as per your requirements (refer to [Configuration Steps](#configuration-steps)).

The configuration files from the `/config/settings` directory are deployed as a part of the AWS CDK deployment process:
* Configuration files are validated and automatically uploaded to the AWS S3 bucket `s3-salmon-settings-<<stage-name>>`.
* The CDK project references these settings from the S3 bucket during runtime, utilizing the configurations to set up the necessary infrastructure.
> **NOTE:**
> If any modifications are made to the configuration files locally, you would need to redeploy the stacks in order to apply the changes to the S3 bucket (refer to [Deployment and installation](deployment.md) for more details).

#### Configuration Structure <a name="conf-structure"></a>
```
project_root/
│
└── config/
    │
    ├── sample_settings/
    │   ├── general.json
    │   ├── monitoring_groups.json
    │   ├── recipients.json
    │   └── replacements.json
    │
    └── settings/
        ├── general.json
        ├── monitoring_groups.json
        ├── recipients.json
        └── replacements.json
```

The project utilizes the following configuration files:
| File Name                | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| `general.json`           | Contains general settings for the tooling environment, monitored environments, and delivery methods. |
| `monitoring_groups.json` | Defines all resources to be monitored, grouped logically. |
| `recipients.json`        | Specifies recipients for alerts and daily digest reports, along with their subscriptions to monitoring groups. |
| `replacements.json`      | [Optional] Contains a replacements list for placeholders in other configuration files. |

## Configuration Steps

Follow these steps to configure the project according to your requirements:

### 1. Create Configuration Files <a name="create-configuration-files"></a>
The initial step is to create the necessary configuration files: **general.json**, **monitoring_groups.json**, **recipients.json**, and **replacements.json** (if required) within the `/config/settings` directory. For a quick start, you can utilize the sample configuration files provided in the `/config/sample_settings` directory.

> **NOTE:**
> Always ensure that the settings you utilize are up-to-date.

### 2. Configure General Settings  <a name="configure-general-settings"></a>
The `general.json` configuration file sets up the tooling environment, monitored environments, and delivery methods. 
```
{
    "tooling_environment": {
        "name": "Tooling Account [<<env>>]",
        "account_id": "<<tooling_account_id>>",
        "region": "eu-central-1",
        "metrics_collection_cron_expression": "cron(*/5 * * * ? *)",
        "digest_report_period_hours" : 24, 
        "digest_cron_expression": "cron(0 8 * * ? *)",
        "grafana_instance": {
            "grafana_vpc_id": "<<grafana_vpc_id>>",
            "grafana_security_group_id": "<<grafana_security_group_id>>"
        }
    },
    "monitored_environments": [
        {
            "name": "Dept1 Account [<<env>>]",
            "account_id": "123456789",
            "region": "eu-central-1",
            "metrics_extractor_role_arn": "arn:aws:iam::123456789:role/role-salmon-cross-account-extract-metrics-dev"
        },
        ...
    ],
    "delivery_methods": [
        {
            "name": "aws_ses",
            "delivery_method_type": "AWS_SES",
            "sender_email" : "<<sender_email>>"
        },
        ...
    ]
}
```     
**Tooling Environment Configuration**:
- `name` - the name of your Tooling environment where SALMON monitoring and alerting infrastructure will be located.

    > Here, `<<env>>` acts as a placeholder that represents the environment name. This allows you to specify a generic name for the tooling account while keeping the option to customize it based on the environment. To define the actual values for placeholders, you can use the replacements.json file (refer to [Configure Replacements for Placeholders](#configure-replacements-for-placeholders)). This file serves as a mapping between placeholders and their corresponding values.
- `account_id`, `region` - AWS region and account ID for the Tooling environment.
- `metrics_collection_cron_expression` - the cron schedule to trigger metrics extraction from Monitored environments.
- `digest_report_period_hours` - how many recent hours should be covered in the Daily Digest report. Default value: `24` hours.
- `digest_cron_expression` - the cron schedule to trigger the Daily Digest report. Default value: `cron(0 8 * * ? *)`, every day at 8am UTC.

**[Optional] Grafana Configuration**: 

If the `grafana_instance` section exists, the Grafana stack will be deployed. Otherwise, it will be skipped.
- `grafana_vpc_id` - the Amazon VPC ID where the Grafana instance will be deployed. At least 1 public subnet required.
- `grafana_security_group_id` - the security group ID that will be associated with the Grafana instance. Inbound access to Grafana’s default HTTP port: 3000 required. 
- (optional) `grafana_key_pair_name`: the name of the key pair to be associated with the Grafana instance. If not provided, a new key pair will be created during the stack deployment.
- (optional) `grafana_bitnami_image`: the Bitnami Grafana image from AWS Marketplace. Default value: `bitnami-grafana-10.2.2-1-r02-linux-debian-11-x86_64-hvm-ebs-nami`.
- (optional) `grafana_instance_type`: the EC2 instance type for the Grafana instance. Default value: `t3.micro`.

To skip the Grafana stack, remove the following `grafana_instance` nested configuration from the `general.json`:
```
        "grafana_instance": {
            "grafana_vpc_id": "<<grafana_vpc_id>>",
            "grafana_security_group_id": "<<grafana_security_group_id>>"
        }
```

**Monitored Environments Configuration**:
- `name` - the name of your Monitored environment.
- `account_id`, `region` - AWS region and account ID of the account to be monitored.
- (optional) `metrics_extractor_role_arn` - IAM Role ARN to be able to extract metrics for the resources running in another AWS account. Default value: `arn:aws:iam::{account_id}:role/role-salmon-cross-account-extract-metrics-dev`. 

You can specify multiple monitored environments.
 
**Delivery Methods Configuration**:
- `name` - the name of your delivery method.
- `delivery_method_type` - the delivery method type (AWS_SES, AWS_SNS, SMTP).

    > The primary delivery method for the current version is AWS SES (with plans to add more options such as SMTP, Slack and MS Teams channel notifications).

    > AWS_SNS method is recommended for alerts only. If you want to receive digest messages, please consider using other delivery method types (as digest requires rich text formatting, which support is limited in SNS).

Based on the delivery method type, additional parameters are required:
* AWS_SES:
    - `sender_email` - the sender email for notifications and digests. Must be verified in AWS SES.
* AWS_SNS:
    - No additional parameters needed. Target SNS topic Arn is configured in recipients section.
* SMTP:
    - `sender_email` - the sender email for notifications and digests.
    - `credentials_secret_name` - the name of the secret stored in AWS Secrets Manager containing the SMTP server credentials. Required key-value pairs: SMTP_SERVER, SMTP_PORT, SMTP_LOGIN, SMTP_PASSWORD. \
    Sample JSON context of the secret:
        ``` json
        {
            "SMTP_SERVER": "put_smtp_host_here",
            "SMTP_PORT": "put_smtp_port_here",
            "SMTP_LOGIN": "put_smtp_login_here",
            "SMTP_PASSWORD": "put_smtp_password_here"
        }
        ```
        > **NOTE:**
        >  The secret in AWS Secrets Manager should have a tag with the key `salmon` and any value. This is required to limit access to only the secrets tagged with `salmon`. 
    - (optional) `use_ssl` - indicate whether to use SSL for the SMTP server connection. If set to True, the connection will use SSL. Otherwhise, STARTTLS will be used. Default value: `True`.
    - (optional) `timeout` -  the connection timeout in seconds. Default value: `10.0`.

You can specify multiple delivery methods (even for the same delivery type, no restrictions).

### 3. Configure Monitoring Groups  <a name="configure-monitoring-groups"></a>
The `monitoring_groups.json` configuration file lists all resources to be monitored, grouped logically. For example, all Glue Jobs and Lambda functions can be related to Data Ingestion Pipeline.
```
{
    "monitoring_groups": [
        {
            "group_name": "pipeline_source1",
            "glue_jobs": [
                {
                    "name": "ds-source1-historical-data-load",
                    "monitored_environment_name": "Dept1 Account [<<env>>]",
                    "sla_seconds": 1200,
                    "minimum_number_of_runs": 0
                },
                {
                    "name": "ds-source1-source-to-raw-full-load",
                    "monitored_environment_name": "Data Lake Account [<<env>>]"
                }
            ],
            "step_functions": [
                {
                    "name": "stepfunction-salmonts-*",
                    "monitored_environment_name": "Dept2 Account [<<env>>]",
                    "sla_seconds": 0
                },
                ...
            ]
        },
        ...
    ]
}
```
**Monitoring Groups Configuration**: 
- `group_name` - the name of your monitoring group.

- For each AWS resource type (such as `glue_jobs`, `step_functions`), a separate subsection should be created. The supported resource types include: **glue_jobs**, **step_functions**, **lambda_functions**, **glue_workflows**, **glue_catalogs**, **glue_crawlers**, **glue_data_quality**, **emr_serverless**. \
Within each section, list the resources of the corresponding resource type along with their properties:

    - `name` - specify the resource name to be monitored.

        >  If you would like to monitor the resources with a common pattern in their names (e.g., glue-pipeline1-ingest, glue-pipeline1-cleanse, glue-pipeline1-staging), use wildcards: glue-pipeline1`-*`. \
        > **NOTE:** Glue Data Quality wildcards are supported only for Rulesets applied to AWS Glue table. For other Rulesets (i.e., executed within AWS Glue job) please specify an exact name (without wildcards). 

        > For EMR Serverless resource type, please specify a name of the EMR Serverless application.

    - `monitored_environment_name` - the name of the Monitored environment (should match to one of the monitored environment names defined in the **general.json** file, **monitored_environments** section, **name** field).
    - (optional) `sla_seconds` - the Service Level Agreement (SLA) in seconds for the resource. If the execution time exceeds the SLA set, such resource run will be marked with the Warning status and and an additional comment will be displayed in the Daily Digest. If this parameter is not set or equals to zero - the check is not applied during the Digest generation. Default value: `0`.
    - (optional) `minimum_number_of_runs` - the minimum number of runs expected for the resource. If there have been less resource runs than expected, such run will be marked with the Warning status and an additional comment will be displayed in the Daily Digest. If this parameter is not set or equals to zero - the check is not applied during the Digest generation. Default value: `0`.

<details>
<summary>Example: Configuring Monitoring Groups based on your resource naming conventions</summary>
  Many companies use AWS resource naming conventions.  

  For example, convention could be: `{type}-{project}-{meaning}-{env}` (result into something like "`job-pnlcalculations-ingestion-dev`" for a Glue job).  

  If you want to monitor all your Glue jobs in project "A" and project "B", but different teams are responsible for managing those projects, an effective strategy is to create two monitoring groups using wildcard statements based on naming conventions.  

  Here's how it can be done:
  ```json
{
    "monitoring_groups": [     
        {
            "group_name": "job_projectA",
            "glue_jobs": [
                {
                    "name": "job-projectA-*",
                    ...
                }
            ]
        },
        {
            "group_name": "job_projectB",
            "glue_jobs": [
                {
                    "name": "job-projectB-*",
                    ...
                }
            ]
        },        
}        
  ```
  The benefits of this approach include:
  1. You can scope all relevant jobs in a single statement without listing all jobs individually, relying on naming conventions.
  2. Any new job created for the project will automatically be included in the monitoring group as long as it follows the naming convention.
  3. Two separate monitoring groups allow you to divide responsibilities between teams. Team "A" can subscribe only to project "A" jobs, while the second team can manage project "B" jobs.  
</details>

### 4. Configure Recipients and Subscriptions  <a name="configure-recipients-and-subscriptions"></a> 
The `recipients.json` file specifies recipients for alerts and digests, along with their subscriptions to the monitoring groups.
```
{
    "recipients": [
        {
            "recipient": "dl-project-admins@salmon.com",
            "delivery_method": "aws_ses",            
            "subscriptions": [
                {
                    "monitoring_group": "pipeline_source1",
                    "alerts": true,
                    "digest": true
                },
                ...
            ]
        },
        ...
    ]
}
```
**Recipients Configuration**:
- `recipient` - an email address of a person / delivery list to receive failure notifications or Daily Digest reports.   
    
    > **NOTE:** for AWS SES method, target email addresses must be verified in AWS SES (verified identities).

    > **NOTE:** put target SNS topic Arn in "recipient" field when using AWS SNS method.

- `delivery_method` - the delivery method name (should match to one of the delivery method names defined in the **general.json** file, **delivery_methods** section, **name** field).
- `monitoring_group` - the monitoring group name (should match to one of the monitoring group names defined in the **monitoring_groups.json** file,  **monitoring_groups** section, **group_name** field).
- `alerts` - indicate whether the recipient would like to receive notifications on failed runs (true/false).
- `digest` - indicate whether the recipient would like to receive Daily Digest (true/false).

### 5. [Optional] Configure Replacements for Placeholders <a name="configure-replacements-for-placeholders"></a> 
The `replacements.json` file provides replacements list for placeholders in other configuration JSON files. Placeholders inside general and other settings should be in double curly brackets (e.g. `<<value>>`). For example, the value for `<<env>>` is defined as `dev`. This means that during the deployment, wherever the `<<env>>` placeholder is used, it will be replaced with `dev`. \
This approach simplifies the process of switching between envrironments by consolidating all environment-specific parameters into the `replacements.json` file.

```
{
    "<<env>>": "dev",
    "<<tooling_account_id>>": "323432554",
    "<<sender_email>>": "salmon-no-reply@soname.de"
}
```
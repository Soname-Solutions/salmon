# SALMON Configuration

## Table of Contents
* [Overview](#overview)
    * [Key Configuration Features](#key-features)
    * [Configuration Structure](#conf-structure)
    * [Deployment Process](#deployment-process)
* [Configuration Steps](#configuration-steps)
    1. [Copy Configuration Samples](#copy-configuration-samples)
    2. [Provide General Settings](#provide-general-settings)
    3. [Configure Monitoring Groups](#configure-monitoring-groups)
    4. [Specify Recipients and Subscriptions ](#specify-recipients-and-subscriptions)
    5. [[Optional] Provide Replacements for Rlaceholders](#provide-replacements-for-placeholders)


## Overview
This guide provides instructions on how to configure the SALMON project to suit your monitoring and alerting needs. 
### Key Configuration Features: <a name="key-features"></a>
* **Extending List Elements** - Each configuration file allows extending list elements, such as `monitored_environments` in `general.json`, with additional blocks of the same structure. This feature facilitates flexibility and scalability in managing configurations. You can effortlessly add or remove entities from the list without altering the file's structure, simplifying adaptation to environmental changes or evolving requirements.
* **Secure Centralized Settings Storage** - All settings reside in a centralized location, namely an AWS S3 bucket, streamlining management and updates. Access to these settings is tightly controlled using AWS IAM policies, ensuring only authorized entities can read or modify configurations.
* **Placeholders** - Some configuration files employ placeholders (e.g., `<<env>>`) enabling dynamic value insertion based on specific requirements. This feature enables the creation of generic configurations easily customizable for different environments or scenarios.
* **Wildcards Support** - To monitor resources sharing a common prefix (e.g., glue-pipeline1-ingest, glue-pipeline1-cleanse, glue-pipeline1-staging), utilize wildcards such as glue-pipeline1`-*` within the `monitoring_groups.json` configuration file.
### Configuration Structure: <a name="conf-structure"></a>
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
| `replacements.json`      | [Optional] Contains a replacements list for placeholders in other setting JSON files. |

### Deployment Process: <a name="deployment-process"></a>
Before the deployment:
* **Prepare Configuration Files**: Sample configurations serving as templates are located at the `/config/sample_settings` directory. Copy these templates to the `/config/settings` directory and fill in the required values as per your requirements (refer to [Configuration Steps](#configuration-steps)).

The configuration files are deployed as a part of the AWS CDK deployment process:
* The settings files located in the `/config/settings` directory are automatically uploaded to the AWS S3 bucket `s3-salmon-settings-<<stage-name>>`.
* The CDK project references these settings from the S3 bucket during runtime, utilizing the configurations to set up the necessary infrastructure.
> **NOTE:**
> If any modifications are made to the configuration files locally, you would need to redeploy the stacks in order to apply the changes to the S3 bucket (refer to [Deployment and installation](deployment.md) for more details).

## Configuration Steps

Follow these steps to configure the project according to your requirements:

### 1. Copy Configuration Samples <a name="copy-configuration-samples"></a>
- Navigate to the `/config/sample_settings` directory
- Copy the sample configuration files (general.json, monitoring_groups.json, recipients.json, and replacements.json if needed) to the `/config/settings` directory

> **NOTE:**
> Always ensure that the settings you utilize are up-to-date.

### 2. Provide General Settings  <a name="provide-general-settings"></a>
The  `general.json` configuration file sets up the tooling environment, monitored environments, and delivery methods. 
```json
{
    "tooling_environment": {
        "name": "Tooling Account [<<env>>]",
        "account_id": "<<tooling_account_id>>",
        "region": "eu-central-1",
        "metrics_collection_interval_min": 5,
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
        }
    ],
    "delivery_methods": [
        {
            "name": "aws_ses",
            "delivery_method_type": "AWS_SES",
            "sender_email" : "<<sender_email>>"
        }
    ]
}
```     
**Tooling Environment Configuration**:
- `name` - the name of your Tolling environment where SALMON monitoring and alerting infrastructure will be located.

    > Here, `<<env>>` acts as a placeholder that represents the environment name. This allows you to specify a generic name for the tooling account while keeping the option to customize it based on the environment. To define the actual values for placeholders, you can use the `replacements.json` file (refer to [Provide Replacements for Rlaceholders](#provide-replacements-for-placeholders)). This file serves as a mapping between placeholders and their corresponding values.
- `account_id`, `region` - AWS region and account ID for the Tolling environment.
- `metrics_collection_interval_min` - an interval (in minutes) for extracting metrics from monitored environments.
- `digest_report_period_hours` - how many recent hours should be covered in the Daily Digest report. Default value: `24` hours.
- `digest_cron_expression` - the cron schedule to trigger the daily digest report. Default value: `cron(0 8 * * ? *)`, every day at 8am UTC.

**[Optional] Grafana Configuration**: 

Only if the `grafana_instance` section exists, the Grafana stack will be deployed. 
If the Grafana stack should be deployed:
- `grafana_vpc_id` - specify the ID of the Amazon VPC where the Grafana instance will be deployed. At least 1 public subnet required.
- `grafana_security_group_id` - specify the ID of the security group that will be associated with the Grafana instance. Inbound access to Grafana’s default HTTP port: 3000 required. 

Additionally, several optional configurations are available to customize the Grafana deployment: 
- `grafana_key_pair_name`: add this parameter and specify the name of the key pair to be associated with the Grafana instance. If not provided, a new key pair will be created during the stack deployment.
- `grafana_bitnami_image`: add this parameter and specify the Bitnami Grafana image from AWS Marketplace. Default value: `bitnami-grafana-10.2.2-1-r02-linux-debian-11-x86_64-hvm-ebs-nami`.
- `grafana_instance_type`: add this parameter and specify the EC2 instance type for the Grafana instance. Default value: `t3.micro`.

If the Grafana deployment should be skipped, remove the following `grafana_instance` nested configuration from the general settings:
```json
        "grafana_instance": {
            "grafana_vpc_id": "<<grafana_vpc_id>>",
            "grafana_security_group_id": "<<grafana_security_group_id>>"
        }
```

**Monitored Environments Configuration**:
- `name` - the name of your Monitored environment. Refered in `monitoring_groups.json`.
- `account_id`, `region` - AWS region and account ID of the account to be monitored.
- [Optional] `metrics_extractor_role_arn` - IAM Role ARN to extract metrics for the resources running in another AWS account. Default value: `arn:aws:iam::{account_id}:role/role-salmon-cross-account-extract-metrics-dev`. 

To specify additional monitored environments, simply append another dictionary block with the same structure.
 
**Delivery Methods Configuration**:
- `name` - the name of your delivery method. Refered in `recipients.json`.
- `delivery_method_type` - the delivery method type (AWS_SES, SMTP).
- `sender_email` - the sender email for notifications and digests.

To specify additional delivery method, simply append another dictionary block with the same structure.

### 3. Configure Monitoring Groups  <a name="configure-monitoring-groups"></a>
The `monitoring_groups.json` configuration file lists all resources to be monitored, grouped logically. For example, all Glue Jobs and Lambda functions can be related to Data Ingestion Pipeline. Inside each group we list group elements with their properties (such as name, sla_seconds, minimum_number_of_runs).
```json
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
                    "monitored_environment_name": "Data Lake Account [<<env>>]",
                    "sla_seconds": 1300,
                    "minimum_number_of_runs": 2
                }
            ]
        }
    ]
}
```
**Monitoring Groups Configuration**: \
- `group_name` - the name of your monitoring pipeline.
- the element `glue_jobs` should be adjusted in accordance with the monitoring resource type (e.g., glue_jobs, step_functions, lambda_functions, glue_workflows, glue_catalogs, glue_crawlers). 
- `name` - specify the resource name to be monitored.

    > If you would like to monitor the resources with the same prefix (e.g., glue-pipeline1-ingest, glue-pipeline1-cleanse, glue-pipeline1-staging), you can simply describe them using wildcards: glue-pipeline1`-*`.

- `monitored_environment_name` - the name of your monitored environment (listed in the general settings).
- [Optional] `sla_seconds` - specify the SLA for the resource execution time if applicable. If the execution time exceeds the SLA set, such resource run will be marked with the Warning status and and an additional comment will be shown in the Daily Digest. If this parameter is not set or equals to zero - the check is not applied during the Digest generation.
- [Optional] `minimum_number_of_runs` - specify the least number of runs expected if applicable. In this case if there have been less actual runs than expected, such resource run will be marked with the Warning status and an additional comment will be shown in the Daily Digest. If this parameter is not set or equals to zero - the check is not applied during the Digest generation.

### 4. Specify Recipients and Subscriptions  <a name="specify-recipients-and-subscriptions"></a> 
The `recipients.json` file specifies recipients for alerts and digests, along with their subscriptions to the monitoring groups.
```json
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
                }
            ]
        }
    ]
}
```
**Recipients Configuration**:
- `recipient` - an email address of a person / delivery list to receive failure notifications or Daily Digest reports.   
    
    > **NOTE:** the email address must be verified in AWS SES.
- `delivery_method` - the delivery method name (specified in the general settings).
- `monitoring_group` - the monitoring group name (specified in the monitoring groups settings).
- `alerts` - indicate whether this recipient would like to receive notifications on failed runs (true/false).
- `digest` - indicate whether this recipient would like to receive Daily Digest (true/false).

### 5. [Optional] Provide Replacements for Rlaceholders <a name="provide-replacements-for-placeholders"></a> 
The `replacements.json` file provides replacements list for placeholders in other setting JSON files. Placeholders inside general and other settings should be in double curly brackets (e.g. `<<value>>`). For example, we defined the value for `<<env>>` as `dev`. This means that during the deployment, wherever the `<<env>>` placeholder is used, it will be replaced with `dev`.

```json
{
    "<<env>>": "dev",
    "<<tooling_account_id>>": "323432554",
    "<<sender_email>>": "salmon-no-reply@soname.de"
}
```
Using the placeholders provides flexibility and consistency in the configuration management. It allows you to define the generic configurations that can be easily customized for different environments or scenarios. This helps to streamline the deployment process and ensures that configurations remain consistent across different deployments.
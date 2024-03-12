# Changelog

All notable changes to this project will be documented in this file.

## 1.0.0

### Alerting functionality
* Designed to catch and publish alerting events to Cloudwatch log group as well as to be notified on failed events.
* Implemented for the following resource types:
     - Glue Crawlers
     - Glue Data Catalogs
     - Glue Jobs
     - Glue Workflows
     - Step Functions

### Data Pipeline Metrics Collection
* Designed to collect metrics for the monitored resources and save them to Timestream database.
* Implemented for the following resource types:
     - Glue Jobs
     - Glue Workflows
     - Step Functions
     - Lambda Functions

### Notifications
* Designed to send formatted messages via provided delivery method.
* Implemented for the following delivery method types:
     - AWS_SES
     - SMTP

### Digest
* Designed to prepare and distribute daily Digest.
* Implemented for the following resource types:
     - Glue Jobs
     - Glue Workflows
     - Step Functions
     - Lambda Functions

### Core functionality
* Deployed using AWS CDK with multiple stacks:
     * Tooling Common stack. Required for provisioning common Salmon components (such as Timestream database, notification service, settings component, SNS topic and SQS FIFO queue).
     * Alerting stack. Required for provisioning alerting Lambda function, CloudWatch log group and stream, alerting Event Bus rule.
     * Monitoring stack. Required for provisioning extract metrics and digest Lambda functions, as well as Timestream tables.
     * Monitored stack. Required for creating cross-account IAM roles to be able to monitor resources across various AWS accounts and regions centrally. 
     * Optional Grafana stack. This enables launching Grafana instance with the following default provisioning dashboards:
          - the dashboard based on the CloudWatch log group with alerting events
          - the dashboard based on the Timestream table with Glue Jobs metrics
          - the dashboard based on the Timestream table with Glue Workflows metrics
          - the dashboard based on the Timestream table with Step Functions metrics
          - the dashboard based on the Timestream table with Lambda Functions metrics   
# Changelog

All notable changes to this project will be documented in this file.

## 1.0.0

### Alerting functionality
* Designed to catch and publish alerting events to Cloudwatch log group. Implemented for the following resource types:
     - Glue Crawlers
     - Glue Data Catalogs
     - Glue Jobs
     - Glue Workflows
     - Step Functions
     - Lambda Functions

* Notifications 
     * Designed to be notified on failed events via provided delivery method. Implemented for AWS SES delivery method type.

### Monitoring capabilities
* Metrics Collection
     * Designed to collect metrics for the monitored resources and store them in the Timestream database. Implemented for the following resource types:
          - Glue Jobs
          - Glue Workflows
          - Step Functions
          - Lambda Functions

* Daily Digest
     * Designed to prepare and distribute daily Digest. Implemented for the following resource types:
          - Glue Jobs
          - Glue Workflows
          - Step Functions
          - Lambda Functions

* Grafana dashboards (optional component)
     * Designed to visualize Metrics and Alerting events. Implemented for the following data sources:
          - CloudWatch log group with Alerting events
          - Timestream table with Glue Jobs metrics
          - Timestream table with Glue Workflows metrics
          - Timestream table with Step Functions metrics
          - Timestream table with Lambda Functions metrics   


### Core components
* Deployed using AWS CDK with multiple stacks:
     * Tooling Common stack
          * Required for provisioning common Salmon components (such as Timestream database, notification service, settings component, SNS topic and SQS FIFO queue).
     * Alerting stack
          * Required for provisioning alerting Lambda function, CloudWatch log group and stream, alerting Event Bus rule.
     * Monitoring stack
          * Required for provisioning extract metrics and digest Lambda functions, as well as Timestream tables.
     * Monitored stack
          * Required for creating cross-account IAM roles to be able to monitor resources across various AWS accounts and regions centrally. 
     * Optional Grafana stack
          * Required for provisioning Grafana instance with the default dashboards. 

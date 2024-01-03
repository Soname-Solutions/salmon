
# Entities

## General settings
Contains the following parts:  
- Tooling environment.  Account and region where our monitoring and alerting infrastructure is located.
- Monitored environment.  List of accounts and regions with resources we want to monitor.
- Used Delivery methods (for notifications and digests)

### Tooling environment

- metrics_collection_interval_min - interval (in minutes) for extracting metrics from monitored environments

#### Grafana settings
The Grafana stack will be deployed only if the Grafana related settings are provided in the "grafana_instance" section, nested within the "tooling_environment" configuration.
The deployment requires two mandatory configurations: "grafana_vpc_id" and "grafana_security_group_id":
- "grafana_vpc_id": the ID of the Amazon VPC where the Grafana instance will be deployed.
- "grafana_security_group_id": the ID of the security group that will be associated with the Grafana instance.

 Additionally, several optional configurations are available to customize the Grafana deployment:
- "grafana_key_pair_name": the name of the key pair to be associated with the Grafana instance. If not provided, a new key pair will be created during the stack deployment.
- "grafana_bitnami_image": the Bitnami Grafana image from AWS Marketplace.
- "grafana_instance_type": the EC2 instance type for the Grafana instance. Defaults to t3.micro.

### Monitored environments notes

- "name": environment name. Refered in items in monitoring_groups.json
- "account_id", "region": refers to AWS Account and Region to be monitored
- "metrics_extractor_role_arn" (Optional field) - Used by tooling account (assumes monitored account role to get access for metrics extraction). If it's omitted - use default (TBD - describe what is default)


- There should be created some artifacts on monitored account, so we can access data (IAM role) and get notifications/alerts (EventBridge Rules).  
IAM Role Arn should be stated in config.
- IAM Role will be created using provided template, so in most cases the name of the role would be the same. The only difference in Arn (e.g. arn:aws:iam::123456789:role/iamr-alertsmon-ingestion-acc-d) is account id.  
So let's introduce a replacement {AccountID}: "MetricsExtractorRoleArn": "arn:aws:iam::{AccountID}:role/iamr-alertsmon-ingestion-acc-d"



## Monitoring groups
Lists all resources to be monitored, grouped logically.
For example, all glue jobs and lambdas related to Data Ingestion Pipeline.

### Monitoring groups notes

- Inside group we list group elements with their properties
- Properties list depends on element type (e.g. Glue Job can have properies such as "name", "sla_seconds", "minimum_number_of_runs")
- Sometime we can have many glue job with the same prefix (like glue-pipeline1-ingest, glue-pipeline1-cleanse, glue-pipeline1-staging).  
It's nice to have the functionality to describe those using wildcards: glue-pipeline1-*

## Recipients
List of recipients (which might be an e-mail, slack channel, teams channel - potentially, extensible in future).
Each recipient is subscribed to one or more "Monitored Groups".
Recipient can opt-in to receive "notifications" and "e-mail digest" (e.g. daily) independently (subscribe to one, but don't subscribe to another).


- Contains recepients (such as individual e-mail, delivery lists, slack channels etc) and their subscription

### Delivery methods settings
Can include 1 or more ways to deliver alerts or daily digests.
If company wants to use AWS SES - place only this one in config section and refer to it's name in Recipients' settings.
For majority communication options some properties / credentials might be needed (e.g. SMTP host, user, pass).
They should be provided as a part of AWS-based secret

**For AWS SES and SMTP delivery methods** - mandatory field "sender_email" (for the field "From")


## Replacements (optional)
Replacements list for placeholders in other setting JSON files.
**Placeholders inside general and other settings should be in double curly brackets (e.g. `<<value>>`)** 
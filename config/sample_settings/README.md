
# Entities

1. General settings
Contains the following parts:  
- Monitored accounts.  List of account with resources we want to monitor.
- Used Delivery methods (for notifications and digests)

2. Monitored groups.
Lists all resources to be monitored, grouped logically.
For example, all glue jobs and lambdas related to Data Ingestion Pipeline.

3. Recipients
List of recipients (which might be an e-mail, slack channel, teams channel - potentially, extensible in future).
Each recipient is subscribed to one or more "Monitored Groups".
Recipient can opt-in to receive "notifications" and "e-mail digest" (e.g. daily) independently (subscribe to one, but don't subscribe to another).

## Monitored accounts notes

- There should be created some artifacts on monitored account, so we can access data (IAM role) and get notifications/alerts (EventBridge Rules).  
IAM Role Arn should be stated in config.
- IAM Role will be created using provided template, so in most cases the name of the role would be the same. The only difference in Arn (e.g. arn:aws:iam::123456789:role/iamr-alertsmon-ingestion-acc-d) is account id.  
So let's introduce a replacement {AccountID}: "MetricsExtractorRoleArn": "arn:aws:iam::{AccountID}:role/iamr-alertsmon-ingestion-acc-d"

## Monitored groups notes

- Inside group we list group elements with their properties
- Properties list depends on element type (e.g. Glue Job can have properies such as "name", "sla_seconds", "minimum_number_of_runs")
- Sometime we can have many glue job with the same prefix (like glue-pipeline1-ingest, glue-pipeline1-cleanse, glue-pipeline1-staging).  
It's nice to have the functionality to describe those using wildcards: glue-pipeline1-*

## Recipients

- Contains recepients (such as individual e-mail, delivery lists, slack channels etc) and their subscription

## Delivery methods settings
Can include 1 or more ways to deliver alerts or daily digests.
If company wants to use AWS SES - place only this one in config section and refer to it's name in Recipients' settings.
For majority communication options some properties / credentials might be needed (e.g. SMTP host, user, pass).
They should be provided as a part of AWS-based secret

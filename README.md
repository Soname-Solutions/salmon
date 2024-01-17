# Soname ALerts and MONitoring (SALMON)

## What is this project for?

We are developing this project to provide an easy-to-use, deploy and maintain system to monitor your AWS-based data pipelines.
Project focuses on AWS services typically used in data processing: Glue, Step Functions, EMR, Lambda etc.

## Typical use-cases

This project can fit your needs if:
- you want to receive immediate notifications when something in your pipeline failes (e.g. Glue Job).
- you want to monitor things like pipeline execution time (e.g. comparing Step Function duration to previous days) and be able to easily identify cases when SLA were missed (e.g. Glue Workflow took longer than expected 45 minutes to complete all the steps).
- you want to receive daily digest e-mail to check if everything runs smoothly or requires your attention
- you have multiple pipelines managed by multiple teams and you'd like to have a setup which sends notification to a specific teams relevant to their pipelines.
- your pipeline resources might be deployed across multiple AWS accounts and regions.

## How SALMON works?

There is a centralized ("tooling") environment where SALMON collects, stores and processes alerts and execution statistics of your data pipelines (even if they are scattered across multiple AWS accounts and regions).

For each AWS account and region where your pipelines are deployed, SALMON requires small portion of resources (EventBridge rule to send alerts to centralized environment and minimal permissions IAM Role, so SALMON can collect pipeline metrics).

![High-Level Diagram](docs/images/high-level-diagram.svg "High-Level Diagram")

For more details please refer to [Solution arhictecture description](docs/architecture.md)

## Monitored services in scope

| AWS Service | Alerts | Metrics |
|:---|:---:|:---:|
| AWS Glue Jobs |       - [x]           |        Metrics         |
| AWS Glue Workflows |       todo:           |        Metrics         |
| AWS Glue Crawlers |       Alerts           |        Metrics         |
| AWS Lambda Functions |       Alerts           |        Metrics         |
| AWS Lambda Functions |       Alerts           |        Metrics         |

todo: add table ( service \\  alerts / metrics collected  )

## How to start

todo:
draft == 

* Prepare config (link -> config and settings)
* Prerequisites: CDK
* Deploy (link -> deployment and installation)

* [Configuration](docs/configuration.md)
* [Deployment and installation](docs/deployment.md)

## Contributing

todo: open issue or pull request

## Other useful links

* [FAQ & Troubleshooting](docs/faq.md)
* [Version history](docs/changes.txt)
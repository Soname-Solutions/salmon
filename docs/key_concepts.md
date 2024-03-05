# SALMON key concepts

This articles describes the core components of SALMON.

**Tooling Environment** - is a set of centralized Salmon components deployed in a specific region of your AWS account (such as metrics history database, notification service, alerts processing components etc.).  

Note: The data pipeline resources you wish to monitor can be located in another and multiple AWS account(s) and region(s).  
Tooling environment can process events/metrics of resources outside of its own account/region.

Configuration file where it is defined: **general.json**.

**Monitored Environments** are created for each AWS account and region where resources you aim to monitor are deployed (e.g. Glue Job, Step functions etc.).  
This includes:
- Eventbridge Rules which send relevant alerts to a centralized EventBus in *Tooling Environment*
- IAM Role which allows *Tooling Environment* extract metrics data (e.g. Glue Job execution statistics). Role's permissions are minimally required.

Configuration file where they are defined: **general.json**.

**Monitoring Groups** - are logical collections of resources you wish to monitor, pointing to AWS resources within your data pipelines. Grouping comes in handy when you have numerous items to monitor.

Some examples of grouping are:
- create group for each project or stream your company manages (e.g. Project "A" has two Step Functions orchestrating the execution of 20 Glue Jobs - they can be logically packed into one monitoring group)
- group resources by responsible operations team

Configuration file where they are defined: **monitoring_groups.json**.

**Recipients** are the entities who receive either alerts or digest messages.
They can be individual emails or email delivery lists. Future plans include adding support for Slack or Microsoft Teams channels as recipients.

Recipients can subscribe to get notification for one or more *monitoring groups*.

Configuration file where they are defined: **recipients.json**.

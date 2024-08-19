# Frequently Asked Questions

**Q: I'm getting an error in my extract-metrics lambda:**  
***Error assuming role arn:aws:iam::{account}:role/role-salmon-monitored-acc-extract-metrics-devam: An error occurred (AccessDenied) when calling the AssumeRole operation: User: arn:aws:sts::{account}:assumed-role/role-salmon-extract-metrics-lambda1-devam/lambda-salmon-extract-metrics-devam is not authorized to perform: sts:AssumeRole on resource: arn:aws:iam::{account}:role/role-salmon-monitored-acc-extract-metrics-devam***

A: Typically this means your monitored environment artifacts were created earlier than an extract metrics IAM Role (which is a part of tooling environment).  
This could have happened due to either an incorrect order of deployment or due to, for example, upgrading a version of tooling environment scripts.  
How to fix:  
you will need to recreate IAM Role in your monitored environment which is done by the following steps:
1. browse to *cdk/monitored_environment* folder.
2. make sure you are using AWS credentials pointing to correct monitored environment (for example you can set AWS_DEFAULT_PROFILE & AWS_DEFAULT_REGION os variables).
3. run ```cdk destroy --context stage-name={stage_name}*```
4. run ```cdk deploy --context stage-name={stage_name}*```

Data pipeline events which happen between step #3 and #4 in this specific monitored environment won't be recorded.
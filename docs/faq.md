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

**Q: Can I use Slack to receive notifications?**

A: Yes, you can configure email alerts to be sent to a Slack channel by following these steps:

1. In your Slack channel, set up the Email App to receive emails. This will provide you with a unique email address for the channel.

![Setting Up Slack Channel](/docs/images/slack-channel.png "Setting Up Slack Channel")

2. In `general.json`, add a delivery method (either AWS_SES or SMTP, depending on your setup). For this delivery method, set `use_inline_css_styles` to True to ensure compatibility with Slack's email rendering.

```json
{
    "delivery_methods": [
        {
            "name": "aws_ses_for_slack",
            "delivery_method_type": "AWS_SES",
            "use_inline_css_styles": true,
            "sender_email" : "no-reply@company.com"
        }   
    ...
    ]
}
```

3. In `recipients.json`, add a recipient for the respective delivery method. Set the recipient to the Slack channel's email address.

```json
{
    "recipients": [
        {
            "recipient": "channel-email-address-slack-gives-you@company.slack.com",
            "delivery_method": "aws_ses_for_slack",
            "subscriptions": [
                {
                    "monitoring_group": "group1",
                    "alerts": true,
                    "digest": true
                }
            ]
        }
        ...
    ]
}                 
```

**Q: My company's policy doesn't allow to creating IAM roles with AdministratorAccess privilege, which CDK bootstrap does by default. Is there a workaround?**

A: Yes, you can bootstrap AWS CDK with less-privileged IAM Role. Please see [Limiting AWS CDK permissions](/docs/limit_cdk_permissions.md) for details.

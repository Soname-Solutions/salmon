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

---

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

---
**Q: How can I configure SMTP delivery method using Gmail Service?**

A: To set up SMTP with Gmail, you need to generate a Gmail App Password, which will be used in the SMTP configuration secret. Follow the instructions here: [Using Gmail App Password](https://support.google.com/mail/answer/185833?hl=en).

Steps to Configure in Salmon:

1. Create a secret in AWS Secrets Manager

The secret should have the following structure:

```json
    {
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_LOGIN": "sender-address@gmail.com",
        "SMTP_PASSWORD": "your-app-password"
    }
```

Replace SMTP_LOGIN and SMTP_PASSWORD with your Gmail credentials.
Ensure the secret has tag `salmon` attache so it is accessible to Salmon's resources.
   
2. Configure the Delivery method in `general.json`:

```json
"delivery_methods": [
    {
        "name": "smtp_gmail",
        "delivery_method_type": "SMTP",
        "sender_email": "sender-address@gmail.com",
        "credentials_secret_name": "secret/smtp/gmail",
        "use_ssl": false
    }
]    
```

---

**Q: Can I receive notifications in Microsoft Teams channel?**

A: Yes, you can configure email alerts to be sent to a MS Teams channel by following these steps:

1. In your MS Teams channel click on "Options" -> "Get email address" to generate a unique email address for the channel.

![Setting Up MS Teams Channel](/docs/images/msteams-channel.png "Setting Up MS Teams Channel")

The following steps are similar to the configuration for any individual email recipient:

2. In `general.json`, add a delivery method (either AWS_SES or SMTP, depending on your setup). 

3. In `recipients.json`, add a recipient for the respective delivery method. Set the recipient to the MS Teams channel's email address.

**Note**: Microsoft Teams has limited support for HTML message formatting. For instance, as of this writing, it does not allow customization of text and background colors.

---

**Q: My company's policy prohibits creating IAM roles with AdministratorAccess privileges, which CDK bootstrap creates by default. Is there a workaround?**

A: Yes, you can bootstrap AWS CDK with a custom IAM policy that limits the privileges of the CloudFormation execution role. This allows you to comply with your company’s security policies while still using CDK. For detailed instructions, refer to [Limiting AWS CDK permissions](/docs/limit_cdk_permissions.md).

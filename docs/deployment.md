
todo:
<<describe prerequisites>>
- cdk bootstrap (if not done) + IAM Role creation (as in ver1 we don't have custom role config)
- local env setup (aws cli, nodejs, cdk) - preferably refer to existing 3rd party docs
- ? AWS profile setup?
- if you use non AWS SES delivery methods - create secrets
- if you use AWS SES - verify recipient's emails
- ... ?

<<describe - prepare json configs and place it properly /config/...>>
- refer to sample configs
- refer to our settings doc

<<describe creation of tooling>>
- what is stage_name

<<describe creation of monitored>>
- mention: for each monitored acc-region
- even if monitored acc-region == tooling acc-region
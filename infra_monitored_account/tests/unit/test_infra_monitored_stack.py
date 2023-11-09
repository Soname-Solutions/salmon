import aws_cdk as core
import aws_cdk.assertions as assertions

from infra_monitored_account.infra_monitored_stack import InfraMonitoredStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infra_monitoring/infra_monitoring_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfraMonitoredStack(app, "infra-monitoring")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

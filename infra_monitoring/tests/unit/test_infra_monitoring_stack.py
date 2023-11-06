import aws_cdk as core
import aws_cdk.assertions as assertions

from infra_monitoring.infra_monitoring_stack import InfraMonitoringStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infra_monitoring/infra_monitoring_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfraMonitoringStack(app, "infra-monitoring")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

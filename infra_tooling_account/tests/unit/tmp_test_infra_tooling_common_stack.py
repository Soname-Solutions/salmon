import aws_cdk as core
import aws_cdk.assertions as assertions

from infra_tooling_account.infra_tooling_common_stack import InfraToolingCommonStack

# example tests. To run these tests, uncomment this file along with the example
# resource in infra_tooling/infra_tooling_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = InfraToolingCommonStack(app, "infra-tooling")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })

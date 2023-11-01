from aws_cdk import (
    # Duration,
    Stack,
    aws_s3 as s3,
    aws_events as events,
    Tags
)
from constructs import Construct

class InfraToolingStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:

        stage_name = kwargs.pop("stage_name", None)

        super().__init__(scope, construct_id, **kwargs)

        test_bucket = s3.Bucket(
            self, 
            "testBucketVd", 
            bucket_name=f"s3-{stage_name}-test",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL
            )

        events.EventBus(
            self, 
            "testEventBusVd", \
            event_bus_name=f"bus-{stage_name}-test"
            )
        


        Tags.of(self).add("stage", stage_name)


        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "InfraToolingQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )

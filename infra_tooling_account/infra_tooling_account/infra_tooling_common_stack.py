from aws_cdk import (
    Stack,
    CfnOutput,
    Tags,
    aws_kms as kms,
    aws_timestream as timestream,
)
from constructs import Construct


class InfraToolingCommonStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        stage_name = kwargs.pop("stage_name", None)
        project_name = kwargs.pop("project_name", None)

        super().__init__(scope, construct_id, **kwargs)

        # AWS Timestream DB
        timestream_kms_key = kms.Key(
            self,
            "salmonTimestreamKMSKey",
            alias=f"key-{project_name}-timestream-{stage_name}",
            description="Key that protects Timestream data",
        )
        timestream_storage = timestream.CfnDatabase(
            self,
            "salmonTimestreamDB",
            database_name=f"timestream-{project_name}-metrics-events-storage-{stage_name}",
            kms_key_id=timestream_kms_key.key_id,
        )

        # Output Timestream DB Arn
        output_timestream_database_arn = CfnOutput(
            self,
            "salmonTimestreamDBArn",
            value=timestream_storage.attr_arn,
            description="The ARN of the Metrics and Events Storage",
            export_name=f"output-{project_name}-metrics-events-storage-arn-{stage_name}",
        )

        Tags.of(self).add("stage_name", stage_name)
        Tags.of(self).add("project_name", project_name)

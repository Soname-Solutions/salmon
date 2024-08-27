import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsgluedq.transforms import EvaluateDataQuality

args = getResolvedOptions(sys.argv, ["JOB_NAME", "S3_BUCKET_NAME", "RULESET_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

s3_bucket_name = args["S3_BUCKET_NAME"]
ruleset_name = args["RULESET_NAME"]

# Script generated for node Amazon S3
AmazonS3_node = glueContext.create_dynamic_frame.from_options(
    format_options={"multiline": False},
    connection_type="s3",
    format="json",
    connection_options={
        "paths": [f"s3://{s3_bucket_name}"],
        "recurse": True,
    },
    transformation_ctx="AmazonS3_node",
)


# Script generated for node Evaluate Data Quality (Multiframe)
ruleset_success = """
    Rules = [
        IsComplete "userId"
    ]
"""

EvaluateDataQualityMultiframe_success = EvaluateDataQuality().process_rows(
    frame=AmazonS3_node,
    ruleset=ruleset_success,
    publishing_options={
        "dataQualityEvaluationContext": ruleset_name,
        "enableDataQualityCloudWatchMetrics": True,
        "enableDataQualityResultsPublishing": True,
    },
    additional_options={"performanceTuning.caching": "CACHE_NOTHING"},
)

job.commit()

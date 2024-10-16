import sys
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ["JOB_NAME"])

# Create a SparkContext and GlueContext
sc = SparkContext()
glueContext = GlueContext(sc)

print("Glue Job SPARK TWO Succeeded!")

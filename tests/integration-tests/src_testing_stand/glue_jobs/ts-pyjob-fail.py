import sys
import random
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext

## @params: [JOB_NAME]
args = getResolvedOptions(sys.argv, ["JOB_NAME"])

# Create a SparkContext and GlueContext
sc = SparkContext()
glueContext = GlueContext(sc)

print("Glue SPARK Job ONE!")

raise Exception("intentional glue job failure - SPARK ONE")

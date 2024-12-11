import boto3
import copy

from inttest_lib.runners.base_resource_runner import BaseResourceRunner
from lib.aws.aws_naming import AWSNaming

PARTITION_VALUE = "2024"
PARTITION_KEY = "ID"
COLUMN_NAME = "Name"
INDEX_NAME = "index1"


class GlueCatalogRunner(BaseResourceRunner):
    def __init__(self, resources_data, region_name, stack_obj):
        super().__init__([], region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.resources_data = resources_data
        self.stack_obj = stack_obj

    def initiate(self):
        # For Glue Data Catalogs, we are testing the number of objects in the Glue database
        # and here we will create a partition and index on the Glue table
        # so to test that there will be one partition and index added

        for glue_db_meaning, glue_table_meaning in self.resources_data.items():
            glue_db_name = AWSNaming.GlueDB(self.stack_obj, glue_db_meaning)
            glue_table_name = AWSNaming.GlueTable(self.stack_obj, glue_table_meaning)
            get_table_response = self.client.get_table(
                DatabaseName=glue_db_name, Name=glue_table_name
            )
            partitions_values = [PARTITION_VALUE]
            # Extract the existing storage descriptor and Create custom storage descriptor with new partition location
            storage_descriptor = get_table_response["Table"]["StorageDescriptor"]
            custom_storage_descriptor = copy.deepcopy(storage_descriptor)
            custom_storage_descriptor["Location"] = (
                storage_descriptor["Location"] + "/".join(partitions_values) + "/"
            )

            # Create new Glue partition
            self.client.create_partition(
                DatabaseName=glue_db_name,
                TableName=glue_table_name,
                PartitionInput={
                    "Values": partitions_values,
                    "StorageDescriptor": custom_storage_descriptor,
                },
            )

            # Create new Glue partition index
            self.client.create_partition_index(
                DatabaseName=glue_db_name,
                TableName=glue_table_name,
                PartitionIndex={"Keys": [PARTITION_KEY], "IndexName": INDEX_NAME},
            )

            print(
                f"Started creation of the partition and index on the Glue table {glue_table_name}."
            )

    def await_completion(self, poll_interval=10):
        # no wait time required for Glue Data Catalogs
        print("All Glue Catalog objects have created.")
        return

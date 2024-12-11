import boto3
import copy

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

PARTITION_VALUE = "2024"
COLUMN_NAME = "ID"
INDEX_NAME = "index1"


class GlueCatalogRunner(BaseResourceRunner):
    def __init__(self, resources_data, region_name):
        super().__init__([], region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.resources_data = resources_data

    def initiate(self):
        for glue_db_name, glue_table_name in self.resources_data.items():
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
                PartitionIndex={"Keys": [COLUMN_NAME], "IndexName": INDEX_NAME},
            )

            print(
                f"Started creation of the partition and index on the Glue table {glue_table_name}."
            )

    def await_completion(self, poll_interval=10):
        print("All Glue Catalog objects have created.")
        return

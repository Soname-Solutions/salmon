import boto3
import copy

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

PARTITIONED_TABLE_NAME = "catalog-table1"
DELETE_TABLE_NAME = "catalog-table2"
PARTITION_VALUE = "2024"
PARTITION_KEY = "ID"
COLUMN_NAME = "Name"
INDEX_NAME = "index1"


class GlueCatalogRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__([resource_names], region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.resource_names = resource_names

    def initiate(self):
        # For Glue Data Catalogs, we are testing the number of objects in the Glue database
        # and here we will create a partition and index on one Glue table to test that there will be one partition and index added
        # and we will delete the second table to test that there will be -1 tables_added

        for glue_db in self.resource_names:
            get_table_response = self.client.get_table(
                DatabaseName=glue_db, Name=PARTITIONED_TABLE_NAME
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
                DatabaseName=glue_db,
                TableName=PARTITIONED_TABLE_NAME,
                PartitionInput={
                    "Values": partitions_values,
                    "StorageDescriptor": custom_storage_descriptor,
                },
            )

            # Create new Glue partition index
            self.client.create_partition_index(
                DatabaseName=glue_db,
                TableName=PARTITIONED_TABLE_NAME,
                PartitionIndex={"Keys": [PARTITION_KEY], "IndexName": INDEX_NAME},
            )
            print(
                f"Started creation of the partition and index on the Glue table {PARTITIONED_TABLE_NAME}."
            )

            # Delete Glue table
            self.client.delete_table(DatabaseName=glue_db, Name=DELETE_TABLE_NAME)

            print(f"Started deletion of the Glue table {DELETE_TABLE_NAME}.")

    def await_completion(self, poll_interval=10):
        # no wait time required for Glue Data Catalogs
        print("All Glue Catalog objects have updated.")
        return

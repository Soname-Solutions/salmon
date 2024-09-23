import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner
from lib.aws.glue_manager import GlueManager


class GlueCrawlerRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.crawler_runs = {}
        self.glue_manager = GlueManager(self.client)

    # Method to start the crawlers
    def initiate(self):
        for crawler_name in self.resource_names:
            _ = self.client.start_crawler(Name=crawler_name)
            self.crawler_runs[crawler_name] = "STARTED"
            print(f"Started Glue Crawler {crawler_name}")

    # Method to wait for the crawlers to complete
    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for crawler_name in self.crawler_runs.keys():
                crawler_data = self.glue_manager.get_crawler_data(crawler_name)
                print(f"Crawler {crawler_name} is in state {crawler_data.State}")
                if not crawler_data.IsCompleted:
                    all_completed = False

            if all_completed:
                break

            # Wait for the specified poll interval before checking again
            time.sleep(poll_interval)

        print("All Glue Crawlers have completed.")

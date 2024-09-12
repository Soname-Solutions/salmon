import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

class GlueCrawlerRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client('glue', region_name=region_name)
        self.crawler_runs = {}

    # Method to start the crawlers
    def initiate(self):
        for crawler_name in self.resource_names:
            response = self.client.start_crawler(Name=crawler_name)
            self.crawler_runs[crawler_name] = 'STARTED'
            print(f"Started Glue Crawler {crawler_name}")

    # Method to wait for the crawlers to complete
    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for crawler_name in self.crawler_runs.keys():
                response = self.client.get_crawler(Name=crawler_name)
                status = response['Crawler']['State']
                print(f"Crawler {crawler_name} is in state {status}")
                # Can't use states from GlueManager (they tailored to alerts)
                # states in boto3 response - just to defect if it's finished or not:
                # 'State': 'READY'|'RUNNING'|'STOPPING'
                if status not in ['READY', 'STOPPING']: 
                    all_completed = False

            if all_completed:
                break

            time.sleep(poll_interval)  # Wait for the specified poll interval before checking again

        print("All Glue Crawlers have completed.")
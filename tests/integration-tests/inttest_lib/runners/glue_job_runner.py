import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

from lib.aws.glue_manager import GlueManager


class GlueJobRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.job_runs = {}

    def initiate(self):
        for job_name in self.resource_names:
            response = self.client.start_job_run(JobName=job_name)
            self.job_runs[job_name] = response["JobRunId"]
            print(f"Started Glue job {job_name} with run ID {response['JobRunId']}")

    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for job_name, run_id in self.job_runs.items():
                response = self.client.get_job_run(JobName=job_name, RunId=run_id)
                status = response["JobRun"]["JobRunState"]
                print(f"Job {job_name} with run ID {run_id} is in state {status}")
                if not GlueManager.is_job_final_state(status):
                    all_completed = False

            if all_completed:
                break

            time.sleep(
                poll_interval
            )  # Wait for the specified poll interval before checking again

        print("All Glue jobs have completed.")

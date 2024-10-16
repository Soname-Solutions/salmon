import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

from lib.aws.glue_manager import GlueManager


class GlueWorkflowRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.workflow_runs = {}

    def initiate(self):
        for workflow_name in self.resource_names:
            response = self.client.start_workflow_run(Name=workflow_name)
            self.workflow_runs[workflow_name] = response["RunId"]
            print(
                f"Started Glue Workflow {workflow_name} with run ID {response['RunId']}"
            )

    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for workflow_name, run_id in self.workflow_runs.items():
                response = self.client.get_workflow_run(
                    Name=workflow_name, RunId=run_id
                )
                status = response["Run"]["Status"]
                print(
                    f"Workflow {workflow_name} with run ID {run_id} is in state {status}"
                )
                if not GlueManager.is_workflow_final_state(status):
                    all_completed = False

            if all_completed:
                break

            time.sleep(
                poll_interval
            )  # Wait for the specified poll interval before checking again

        print("All Glue workflows have completed.")

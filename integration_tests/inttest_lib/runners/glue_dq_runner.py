import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner
from lib.aws.aws_naming import AWSNaming

DQ_MEANING = "dq"


class GlueDQRunner(BaseResourceRunner):
    def __init__(self, resource_names, region_name, started_after):
        super().__init__(resource_names, region_name)
        self.client = boto3.client("glue", region_name=region_name)
        self.started_after = started_after

    def initiate(self):
        for ruleset__name in self.resource_names:
            response = self.client.start_data_quality_ruleset_evaluation_run(
                DataSource={
                    "GlueTable": {
                        "DatabaseName": AWSNaming.GlueDB(self, DQ_MEANING),
                        "TableName": AWSNaming.GlueTable(self, DQ_MEANING),
                    }
                },
                Role=AWSNaming.IAMRole(self, DQ_MEANING),
                RulesetNames=[ruleset__name],
            )
            print(
                f"Started Glue DQ Ruleset {ruleset__name} with run ID {response['RunId']}"
            )

    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True

            response_1 = self.client.list_data_quality_results(
                Filter={"StartedAfter": self.started_after}
            )
            result_ids = [x["ResultId"] for x in response_1["Results"]]
            response_2 = self.client.batch_get_data_quality_result(ResultIds=result_ids)
            ruleset_names = [
                result["RulesetName"] for result in response_2.get("Results", [])
            ]

            # check if the all rulesetes monitored are finished
            incomplete_rulesets = [
                name for name in self.resource_names if name not in ruleset_names
            ]

            if incomplete_rulesets:
                all_completed = False

            if all_completed:
                break

            time.sleep(
                poll_interval
            )  # Wait for the specified poll interval before checking again

        print("All Glue Rulesets have completed.")

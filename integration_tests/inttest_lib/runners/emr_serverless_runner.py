import boto3
import time

from inttest_lib.runners.base_resource_runner import BaseResourceRunner

from lib.aws.emr_manager import EMRManager, EMRJobRunData

SCRIPTS_S3_BUCKET_PREFIX = "emr-scripts"
EXEC_IAM_ROLE_MEANING = "emr-serverless-exec"
EMRS_TAG_FOR_PERMISSION_JSON = {"salmon" : "for permissions"}

def get_scripts_s3_bucket_meaning(aws_account_id):
    return f"{SCRIPTS_S3_BUCKET_PREFIX}-{aws_account_id}"

class EMRServerlessJobRunner(BaseResourceRunner):
    def __init__(self, emr_resources_data: dict, region_name, execution_role_arn, scripts_s3_bucket):
        # instead of resource_names we require emr_resources_data dict in a form of
        # { "app_NAME" : ["script_to_run_path1", "script_to_run_path2"]}
        super().__init__([], region_name)        
        self.client = boto3.client('emr-serverless', region_name=region_name)
        self.emr_resources_data = emr_resources_data
        self.execution_role_arn = execution_role_arn
        self.scripts_s3_bucket = scripts_s3_bucket
        self.emr_manager = EMRManager(self.client)
        self.job_runs = {}

    def initiate(self):
        for app_name, script_paths in self.emr_resources_data.items():
            app_id = self.emr_manager.get_application_id_by_name(app_name)
            print(f"Processing app: {app_name} -> {app_id}")

            for script_path in script_paths:
                print(f"Running script {script_path}")

                response = self.client.start_job_run(
                    applicationId=app_id,
                    executionRoleArn=self.execution_role_arn,
                    # required for permissions
                    tags=EMRS_TAG_FOR_PERMISSION_JSON,
                    jobDriver={
                        'sparkSubmit': {
                            'entryPoint': f's3://{self.scripts_s3_bucket}/{script_path}',
                            'sparkSubmitParameters': '--conf spark.executor.memory=2g --conf spark.executor.cores=2'
                        }
                    },
                    configurationOverrides={
                        'monitoringConfiguration': {
                            's3MonitoringConfiguration': {
                                'logUri': f's3://{self.scripts_s3_bucket}/logs/'
                            }
                        }
                    }
                )
                job_run_id = response['jobRunId']
                self.job_runs[script_path] = {"app_id" : app_id, "job_run_id": job_run_id}
                print(f"Started EMR Serverless job {script_path} with run ID {job_run_id}")

    def await_completion(self, poll_interval=10):
        while True:
            all_completed = True
            for script_path, job_run_data in self.job_runs.items():
                app_id = job_run_data["app_id"]
                job_run_id = job_run_data["job_run_id"]
                job_run: EMRJobRunData = self.emr_manager.get_job_run(app_id=app_id, run_id=job_run_id)

                print(f"Job {script_path} with run ID {job_run_id} is in state {job_run.state}")
                if not(EMRManager.is_final_state(job_run.state)):
                    all_completed = False

            if all_completed:
                break

            time.sleep(poll_interval)  # Wait for the specified poll interval before checking again

        print("All EMR Serverless jobs have completed.")
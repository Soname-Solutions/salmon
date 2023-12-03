import boto3

class GlueManagerException(Exception):
    """Exception raised for errors encountered while running Glue client methods."""

    pass

class GlueManager:
    def __init__(self, glue_client=None):
        self.glue_client = boto3.client("glue") if glue_client is None else glue_client

    def get_all_job_names(self):
        try:
            response = self.glue_client.list_jobs()
            return response.get('JobNames')

        except Exception as e:
            error_message = f"Error getting list of glue jobs : {e}"
            raise GlueManagerException(error_message)            


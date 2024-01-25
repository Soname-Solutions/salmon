import boto3
import logging
from abc import ABC, abstractmethod

from lib.aws.timestream_manager import TimeStreamQueryRunner


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DigestException(Exception):
    pass


class BaseDigestDataExtractor(ABC):
    """
    Base Class which provides unified functionality for extracting runs for the digest report.

    """

    def __init__(self, resource_type, timestream_db_name, timestream_table_name):
        self.resource_type = resource_type
        self.timestream_db_name = timestream_db_name
        self.timestream_table_name = timestream_table_name

    @abstractmethod
    def get_query(self, start_time):
        pass

    def extract_runs(self, query):
        timestream_query_client = boto3.client("timestream-query")
        query_runner = TimeStreamQueryRunner(
            timestream_query_client=timestream_query_client
        )
        output_dict = {}

        try:
            if not (
                query_runner.is_table_empty(
                    self.timestream_db_name, self.timestream_table_name
                )
            ):
                result = query_runner.execute_query(query)
                output_dict[self.resource_type] = result
            else:
                logger.info(
                    f"No data in table {self.timestream_table_name}, skipping.."
                )

            return output_dict

        except Exception as e:
            logger.error(e)
            error_message = f"Error extracting digest data: {e}"
            raise DigestException(error_message)


class GlueJobsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Jobs runs.
    """

    def get_query(self, start_time):
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then job_run_id else '' end as job_run_id, execution, failed, succeeded, execution_time_sec, """
            f""" case when error_message is null then 'Error' else error_message end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND now()  """
        )
        print(query)

        return query


class GlueWorkflowsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Workflows runs.
    """

    def get_query(self, start_time):
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then workflow_run_id else '' end as job_run_id, execution, actions_failed as failed, """
            f""" actions_succeeded as succeeded, null as execution_time_sec, error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND now() """
        )
        return query


class GlueCrawlersDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Crawlers runs.
    """

    def get_query(self, start_time):
        query = ()  # to be implemented
        return query


class GlueDataCatalogsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Data Catalogs runs.
    """

    def get_query(self, start_time):
        query = ()  # to be implemented
        return query


class StepFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Step Functions runs.
    """

    def get_query(self, start_time):
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then step_function_run_id else '' end as job_run_id, execution, failed, """
            f""" succeeded, duration_sec as execution_time_sec, 'Error' as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND now() """
        )
        return query


class LambdaFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Lambda Funstions runs.
    """

    def get_query(self, start_time):
        query = ()  # to be implemented
        return query

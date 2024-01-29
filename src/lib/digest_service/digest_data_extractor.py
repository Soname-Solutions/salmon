import boto3
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from lib.aws.timestream_manager import TimeStreamQueryRunner


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DigestException(Exception):
    pass


class BaseDigestDataExtractor(ABC):
    """
    Base Class which provides unified functionality for extracting runs for the digest report.

    """

    def __init__(
        self, resource_type: str, timestream_db_name: str, timestream_table_name: str
    ):
        self.resource_type = resource_type
        self.timestream_db_name = timestream_db_name
        self.timestream_table_name = timestream_table_name

    @abstractmethod
    def get_query(self, start_time: datetime, end_time: datetime):
        pass

    def extract_runs(self, query: str) -> dict:
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

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then job_run_id else '' end as job_run_id, execution, failed, succeeded, execution_time_sec, """
            f""" case when failed > 0 then error_message else '' end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}'  """
        )
        return query


class GlueWorkflowsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Workflows runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then workflow_run_id else '' end as job_run_id, execution, failed, """
            f""" succeeded, execution_time_sec, case when failed > 0 then error_message else '' end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}' """
        )
        return query


class GlueCrawlersDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Crawlers runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        # columns to be re-checked
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then crawler_run_id else '' end as job_run_id, execution, failed, """
            f""" succeeded, execution_time_sec, case when failed > 0 then error_message else '' end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}' """
        )
        return query


class GlueDataCatalogsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Data Catalogs runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        # columns to be re-checked
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then catalog_run_id else '' end as job_run_id, execution, failed, """
            f""" succeeded, execution_time_sec, case when failed > 0 then error_message else '' end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}' """
        )
        return query


class StepFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Step Functions runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = (
            f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, """
            f""" case when failed > 0 then step_function_run_id else '' end as job_run_id, execution, failed, """
            f""" succeeded, duration_sec as execution_time_sec, case when failed > 0 then error_message else '' end as error_message """
            f"""FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}' """
        )
        return query


class LambdaFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Lambda Funstions runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = (
            f""" SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, execution, failed,  """
            f"""     succeeded, execution_time_sec, error_message  """
            f""" FROM (  """
            f""" SELECT  monitored_environment, resource_name, sum(execution) as execution, 0 as failed,   """
            f"""         sum(execution) as succeeded, round(max(duration_ms)/60, 2) as execution_time_sec, error_message  """
            f""" FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}' """
            f""" AND measure_name = 'execution'  """
            f""" GROUP BY monitored_environment, resource_name,  error_message  """
            f""" UNION ALL  """
            f""" SELECT  monitored_environment, resource_name, count(measure_name) as execution, count(measure_name) as failed,   """
            f"""         0 as  succeeded, round(max(duration_ms)/60, 2) as execution_time_sec, error_message   """
            f""" FROM "{self.timestream_db_name}"."{self.timestream_table_name}" WHERE time BETWEEN '{start_time}' AND '{end_time}'  """
            f""" AND measure_name = 'error'  """
            f""" GROUP BY monitored_environment, resource_name,  error_message) t  """
        )
        return query

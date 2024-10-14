import boto3
import logging
from abc import ABC, abstractmethod
from datetime import datetime

from lib.aws.timestream_manager import TimeStreamQueryRunner
from lib.aws.glue_manager import GlueManager

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
        # safety precautions for services where queries are not yet implemented
        if not (query):
            return {}

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
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                     , case when failed > 0 then job_run_id else '' end as job_run_id, execution
                     , failed, succeeded, execution_time_sec
                     , case when failed > 0 then error_message else '' end as error_message
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}"
                WHERE time BETWEEN '{start_time}' AND '{end_time}'
            """
        return query


class GlueWorkflowsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Workflows runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                     , case when failed > 0 then workflow_run_id else '' end as job_run_id, execution
                     , failed, succeeded, execution_time_sec
                     , case when failed > 0 then error_message else '' end as error_message 
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}" 
                WHERE time BETWEEN '{start_time}' AND '{end_time}'
            """
        return query


class GlueCrawlersDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Crawlers runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                         , CASE WHEN failed > 0 THEN crawl_id ELSE '' END as job_run_id
                         , execution, failed, succeeded, duration_sec as execution_time_sec
                         , CASE WHEN failed > 0 THEN error_message ELSE '' END as error_message 
                      FROM "{self.timestream_db_name}"."{self.timestream_table_name}" 
                     WHERE time BETWEEN '{start_time}' AND '{end_time}' 
            """
        return query


class GlueDataCatalogsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Data Catalogs runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        print("Calling a method which hasn't been implemented yet")
        query = ""
        return query


class GlueDataQualityDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Glue Data Quality runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                     , case when failed > 0 and context_type = '{GlueManager.DQ_Catalog_Context_Type}' then ruleset_run_id
                            when failed > 0 and context_type = '{GlueManager.DQ_Job_Context_Type}' then glue_job_run_id 
                       else '' end as job_run_id
                     , execution, failed, succeeded, execution_time_sec
                     , case when failed > 0 then error_message else '' end as error_message
                     , context_type, glue_table_name, glue_db_name, glue_job_name  
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}" 
                WHERE time BETWEEN '{start_time}' AND '{end_time}' 
            """
        return query


class StepFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Step Functions runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                     , case when failed > 0 then step_function_run_id else '' end as job_run_id
                     , execution, failed, succeeded, duration_sec as execution_time_sec
                     , case when failed > 0 then error_message else '' end as error_message  
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}"
                WHERE time BETWEEN '{start_time}' AND '{end_time}' 
            """
        return query


class LambdaFunctionsDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting Lambda Functions attempts.
    In case of Lambda retries, the latest attempt will be considered.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name, job_run_id
                         , execution, failed, succeeded, execution_time_sec, error_message
                    FROM (
                            SELECT monitored_environment, resource_name, '' as job_run_id
                                 , attempt as execution, failed, succeeded, round(duration_ms/60, 2) as execution_time_sec
                                 , case when failed > 0 then error_message else '' end as error_message
                                 , row_number() over (partition by lambda_function_request_id order by time desc) as rn
                            FROM "{self.timestream_db_name}"."{self.timestream_table_name}"
                            WHERE time BETWEEN '{start_time}' AND '{end_time}')  t
                    WHERE rn = 1
                """
        return query


class EMRServerlessDigestDataExtractor(BaseDigestDataExtractor):
    """
    Class is responsible for preparing the query for extracting EMR Serverless runs.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""SELECT '{self.resource_type}' as resource_type, monitored_environment, resource_name
                     , case when failed > 0 then job_run_id else '' end as job_run_id
                     , execution, failed, succeeded, execution_time_sec
                     , case when failed > 0 then error_message else '' end as error_message  
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}"
                WHERE time BETWEEN '{start_time}' AND '{end_time}' 
            """
        return query

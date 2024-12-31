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
    Base Class which provides unified functionality for extracting runs used in the digest report.
    """

    def __init__(
        self, resource_type: str, timestream_db_name: str, timestream_table_name: str
    ):
        self.resource_type = resource_type
        self.timestream_db_name = timestream_db_name
        self.timestream_table_name = timestream_table_name

    @abstractmethod
    def get_query(self, start_time: datetime, end_time: datetime) -> str:
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
    Class is responsible for preparing the query for extracting Glue Data Catalogs counts.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""
                WITH ranked_records AS(
                    SELECT
                      t.*
                      , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS rn_desc
                      , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time ASC) AS rn_asc
                    FROM "{self.timestream_db_name}"."{self.timestream_table_name}" t
                    WHERE time BETWEEN '{start_time}' AND '{end_time}'
                ),
                -- filter to retain only the earliest and latest rows for each resource
                min_max_record AS (
                    SELECT *
                    FROM ranked_records
                    WHERE rn_desc = 1 OR rn_asc = 1
                ),
                -- get previous counts for tables, partitions, and indexes
                counts AS (
                    SELECT
                        monitored_environment
                      , resource_name 
                      , tables_count
                      , LAG(tables_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_tables_count
                      , partitions_count
                      , LAG(partitions_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_partitions_count
                      , indexes_count
                      , LAG(indexes_count) OVER (PARTITION BY resource_name ORDER BY time) AS prev_indexes_count
                      , ROW_NUMBER() OVER (PARTITION BY resource_name ORDER BY time DESC) AS row_num
                    FROM min_max_record
                )
                --final results
                SELECT 
                     '{self.resource_type}' as resource_type
                     , monitored_environment
                     , resource_name
                     , tables_count
                     , COALESCE(tables_count - prev_tables_count, 0) AS tables_added
                     , partitions_count
                     , COALESCE(partitions_count - prev_partitions_count, 0) AS partitions_added
                     , indexes_count
                     , COALESCE(indexes_count - prev_indexes_count, 0) AS indexes_added
                FROM counts
                WHERE row_num = 1
                """
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
    Class is responsible for preparing the query for extracting Lambda Functions invocations.
    """

    def get_query(self, start_time: datetime, end_time: datetime) -> str:
        query = f"""
                -- Aggregate error messages by lambda_function_request_id
                WITH ids AS(
                    SELECT lambda_function_request_id
                         , ARRAY_JOIN(ARRAY_AGG(error_message), ', ') AS error_message
                    FROM "{self.timestream_db_name}"."{self.timestream_table_name}"
                    WHERE time BETWEEN '{start_time}' AND '{end_time}'
                    GROUP BY lambda_function_request_id
                ) 
                SELECT  '{self.resource_type}' AS resource_type
                        , t.monitored_environment
                        , t.resource_name
                        , t.lambda_function_request_id AS job_run_id
                        , t.log_stream
                        , ids.error_message
                        , 1 AS execution
                        , MIN(t.failed) AS failed
                        , MAX(t.succeeded) AS succeeded
                        , ROUND(SUM(t.duration_ms)/1000, 2) AS execution_time_sec                                
                        , SUM(t.failed) AS failed_attempts
                FROM "{self.timestream_db_name}"."{self.timestream_table_name}" t
                JOIN ids 
                  ON t.lambda_function_request_id=ids.lambda_function_request_id
                GROUP BY 
                          t.monitored_environment
                        , t.resource_name
                        , t.lambda_function_request_id
                        , t.log_stream
                        , ids.error_message                 
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

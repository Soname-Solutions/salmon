from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor

from lib.aws.glue_manager import GlueManager, JobRun

class GlueCrawlersMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue crawlers metrics
    """

    def _extract_metrics_data(self, since_time: datetime) -> list[JobRun]:
        glue_man = GlueManager(super().get_aws_service_client())
        job_runs = glue_man.get_job_runs(
            job_name=self.resource_name, since_time=since_time
        )
        return job_runs    

    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):
        # job_runs = self._extract_metrics_data(since_time=since_time)
        # records, common_attributes = self._data_to_timestream_records(job_runs)
        # return records, common_attributes
            
        print("Calling a method which hasn't been implemented yet")
        return [], {}
        # todo: requires implementation

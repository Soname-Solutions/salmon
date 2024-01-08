from datetime import datetime
from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor


class LambdaFunctionsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue job metrics
    """ 

    def prepare_metrics_data(self, since_time: datetime) -> (list, dict):
        print("Calling a method which hasn't been implemented yet")
        return [],{}
        # todo: requires implementation
      
        

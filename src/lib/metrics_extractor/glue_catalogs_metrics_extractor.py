from datetime import datetime, timezone

from lib.metrics_extractor.base_metrics_extractor import BaseMetricsExtractor
from lib.aws.glue_manager import GlueManager, CatalogData
from lib.core import datetime_utils


class GlueCatalogsMetricExtractor(BaseMetricsExtractor):
    """
    Class is responsible for extracting glue catalogs metrics
    """

    def _extract_metrics_data(self) -> CatalogData:
        glue_man = GlueManager(super().get_aws_service_client())
        return glue_man.get_catalog_data(db_name=self.resource_name)

    def _data_to_timestream_records(self, catalog_data: CatalogData) -> list:
        common_dimensions = [
            {"Name": "monitored_environment", "Value": self.monitored_environment_name},
            {"Name": self.RESOURCE_NAME_COLUMN_NAME, "Value": self.resource_name},
        ]

        common_attributes = {"Dimensions": common_dimensions}
        dimensions = [{"Name": "catalog_id", "Value": catalog_data.CatalogID}]

        metric_values = [
            ("tables_count", int(catalog_data.TotalTableCount), "BIGINT"),
            ("partitions_count", int(catalog_data.TotalPartitionsCount), "BIGINT"),
            ("indexes_count", int(catalog_data.TotalIndexesCount), "BIGINT"),
        ]
        measure_values = [
            {
                "Name": metric_name,
                "Value": str(metric_value),
                "Type": metric_type,
            }
            for metric_name, metric_value, metric_type in metric_values
        ]

        current_time = datetime.now(tz=timezone.utc)
        record_time = datetime_utils.datetime_to_epoch_milliseconds(current_time)
        records = [
            {
                "Dimensions": dimensions,
                "MeasureName": self.COUNT_MEASURE_NAME,
                "MeasureValueType": "MULTI",
                "MeasureValues": measure_values,
                "Time": record_time,
                "TimeUnit": "MILLISECONDS",
            }
        ]

        return records, common_attributes

    def prepare_metrics_data(self, since_time: datetime) -> tuple[list, dict]:
        catalog_data = self._extract_metrics_data()
        records, common_attributes = self._data_to_timestream_records(catalog_data)
        return records, common_attributes

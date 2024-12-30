from typing import Type

from lib.metrics_storage.base_metrics_storage import (
    BaseMetricsStorage,
    MetricsStorageTypes as types,
)
from lib.metrics_storage.timestream_metrics_storage import TimestreamMetricsStorage


class MetricsStorageProvider:
    _metrics_storages: dict[str, Type[BaseMetricsStorage]] = {}

    @staticmethod
    def register_metrics_storage(
        metrics_storage_type: str, metrics_storage: Type[BaseMetricsStorage]
    ):
        MetricsStorageProvider._metrics_storages[metrics_storage_type] = metrics_storage


MetricsStorageProvider.register_metrics_storage(
    types.AWS_TIMESTREAM, TimestreamMetricsStorage
)

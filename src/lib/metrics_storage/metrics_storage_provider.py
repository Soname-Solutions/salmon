from typing import Type

from lib.metrics_storage.base_metrics_storage import BaseMetricsStorage
from lib.metrics_storage.timestream_metrics_storage import TimestreamMetricsStorage


class MetricsStorageTypes:
    AWS_TIMESTREAM = "aws_timestream"


class MetricsStorageProvider:
    _metrics_storages: dict[str, Type[BaseMetricsStorage]] = {}

    @staticmethod
    def register_metrics_storage(
        metrics_storage_type: str, metrics_storage: Type[BaseMetricsStorage]
    ):
        MetricsStorageProvider._metrics_storages[metrics_storage_type] = metrics_storage

    @staticmethod
    def get_metrics_storage(metrics_storage_type: str, **kwargs) -> BaseMetricsStorage:
        storage_class = MetricsStorageProvider._metrics_storages.get(
            metrics_storage_type
        )

        if not storage_class:
            raise ValueError(
                f"Metrics storage for type = {metrics_storage_type} is not registered."
            )

        return storage_class(**kwargs)


MetricsStorageProvider.register_metrics_storage(
    MetricsStorageTypes.AWS_TIMESTREAM, TimestreamMetricsStorage
)

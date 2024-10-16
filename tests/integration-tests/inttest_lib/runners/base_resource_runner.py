from abc import ABC, abstractmethod


class BaseResourceRunner(ABC):
    def __init__(self, resource_names, region_name):
        self.resource_names = resource_names
        self.region_name = region_name

    @abstractmethod
    def initiate(self):
        pass

    @abstractmethod
    def await_completion(self, poll_interval=10):
        pass

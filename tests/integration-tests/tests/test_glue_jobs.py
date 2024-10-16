from lib.core.constants import SettingConfigResourceTypes

from test_base_class import TestBaseClass


class TestGlueJobs(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.GLUE_JOBS

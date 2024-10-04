from lib.core.constants import SettingConfigResourceTypes

from test_base_class import TestBaseClass


class TestEMRServerless(TestBaseClass):
    __test__ = True  # to override BaseClass' skip

    @classmethod
    def setup_class(cls):
        cls.resource_type = SettingConfigResourceTypes.EMR_SERVERLESS
        cls.cloudwatch_detail_type = "EMR Serverless Job Run State Change"

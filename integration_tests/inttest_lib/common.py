import json
import os
import sys
from types import SimpleNamespace

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
lib_path = os.path.join(project_root, 'src')
sys.path.append(lib_path)

from lib.core.constants import SettingConfigResourceTypes
from lib.aws.aws_naming import AWSNaming

TARGET_MEANING = "inttest-target"
PROJECT_NAME = "salmon"

def get_resource_name_meanings(resource_type: str) -> list[str]:
    """
        Lists all resources of specific type which is in testing scope.
        Return not exactly the names of resources, but, for better compatibility - their "meanings"
        So fulle resources names should be reconstructed by AWSNaming.<Resource>(stack, meaning)
    """
    config_filename = os.path.join(os.path.dirname(__file__), '..', 'config.json')

    with open(config_filename,'r') as config_file:
        config_data = json.load(config_file)
        resources = config_data.get("scoped_resource_meanings",{})

        return resources.get(resource_type,[])

def get_stack_obj_for_naming(stage_name):
    return SimpleNamespace(project_name = PROJECT_NAME, stage_name = stage_name)

def get_testing_stand_resource_names(stage_name, stack_obj_for_naming = None):
    if stack_obj_for_naming is None:
        stack_obj_for_naming = get_stack_obj_for_naming(stage_name)

    glue_jobs = SettingConfigResourceTypes.GLUE_JOBS
    testing_stand_resources = {
        glue_jobs : [AWSNaming.GlueJob(stack_obj_for_naming, meaning) for meaning in get_resource_name_meanings(glue_jobs)]
    }    

    return testing_stand_resources

def get_target_sns_topic_name(stage_name: str) -> str:    
    return AWSNaming.SNSTopic(stack_obj=get_stack_obj_for_naming(stage_name), meaning=TARGET_MEANING)

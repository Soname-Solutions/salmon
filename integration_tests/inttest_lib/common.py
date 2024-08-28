import json
import os
import sys
from types import SimpleNamespace

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
lib_path = os.path.join(project_root, "src")
sys.path.append(lib_path)

from lib.aws.aws_naming import AWSNaming

TARGET_MEANING = "inttest-target"
PROJECT_NAME = "salmon"

def get_stack_obj_for_naming(stage_name):
    return SimpleNamespace(project_name=PROJECT_NAME, stage_name=stage_name)

def get_target_sns_topic_name(stage_name: str) -> str:
    return AWSNaming.SNSTopic(
        stack_obj=get_stack_obj_for_naming(stage_name), meaning=TARGET_MEANING
    )

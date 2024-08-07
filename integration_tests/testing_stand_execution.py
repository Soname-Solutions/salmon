import argparse
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
lib_path = os.path.join(project_root, 'src')
sys.path.append(lib_path)

from inttest_lib.runners.base_resource_runner import BaseResourceRunner
from inttest_lib.runners.glue_job_runner import GlueJobRunner

from inttest_lib.time_helper import epoch_to_utc_string

def main():
    import time
    current_epoch_seconds = int(time.time())*1000
    print(f"Current time in epoch seconds: {current_epoch_seconds}")

    # 1. prepare
    parser = argparse.ArgumentParser(description="Process some settings.")
    parser.add_argument("--stage-name", required=True, type=str, help="stage-name")
    parser.add_argument("--region", required=True, type=str, help="region")
    args = parser.parse_args()

    stage_name = args.stage_name
    region = args.region

    # 2. run testing stand resources
    glue_job_names = [f"glue-salmon-pyjob-success-{stage_name}", f"glue-salmon-pyjob-fail-{stage_name}"]
    runner = GlueJobRunner(resource_names = glue_job_names, region_name = region)

    runner.initiate()

    runner.await_completion( poll_interval = 5 )

    # 3. execute extract-metrics-orch lambda (in async mode, so if failure - destination would work)
    # todo:

if __name__ == "__main__":
    main()
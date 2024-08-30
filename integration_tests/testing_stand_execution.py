import argparse
import time

from inttest_lib.testing_stand_executor import TestingStandExecutor

if __name__ == "__main__":
    # 1. Parse Arguments
    parser = argparse.ArgumentParser(description="Process some settings.")
    parser.add_argument("--stage-name", required=True, type=str, help="stage-name")
    parser.add_argument("--region", required=True, type=str, help="region")
    parser.add_argument(
        "--resource-types",
        type=str,
        help="Comma separated list of resource types to run (e.g. glue_jobs,glue_workflows) or 'all'",
        default="all",
    )
    args = parser.parse_args()

    if args.resource_types.strip().lower() == "all":
        resource_types = None
    else:
        resource_types = [rt.strip() for rt in args.resource_types.split(",")]

    current_epoch_msec = int(time.time()) * 1000
    print(
        f"Current time in epoch milliseconds: {current_epoch_msec}. Pytest param: --start-epochtimemsec={current_epoch_msec}"
    )

    # 2. Run TestingStandExecutor
    executor = TestingStandExecutor(args.stage_name, args.region, args.resource_types)
    executor.run_workloads()
    executor.await_workloads()
    executor.conclude()

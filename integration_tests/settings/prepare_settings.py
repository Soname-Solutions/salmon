import boto3
import json
import os
import argparse
import sys
sys.path.append("../../integration_tests")
from inttest_lib.common import get_target_sns_topic_name

# this script is executed before CDK deploy, it prepares settings (e.g. replaces variable parts such as AWS account ID etc.)
# The script can be modified for any specific set of config files


def get_aws_account_id():
    session = boto3.Session()
    sts_client = session.client("sts")
    response = sts_client.get_caller_identity()
    account_id = response["Account"]
    return account_id


def read_replacements_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def update_replacements_file(file_path, replacements_dict):
    data = read_replacements_file(file_path)
    for key, value in replacements_dict.items():
        data[key] = value

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "replacements.json")

    parser = argparse.ArgumentParser(description='Process some settings.')
    parser.add_argument('--stage-name', required=True, type=str, help='stage-name')
    parser.add_argument('--region-name', required=True, type=str, help='region-name')
    args = parser.parse_args()

    stage_name = args.stage_name

    replacements_dict = {
        "<<main_account_id>>": get_aws_account_id(),
        "<<stage_name>>": stage_name,
        "<<region>>": args.region_name,
        "<<target_topic_name>>": get_target_sns_topic_name(stage_name=stage_name)
    }

    update_replacements_file(file_path, replacements_dict)
    print(f"Replacements applied to replacements.json: {json.dumps(replacements_dict, indent=4)}")

if __name__ == "__main__":
    main()

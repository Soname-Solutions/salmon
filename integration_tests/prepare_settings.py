import json
import os
import argparse

from inttest_lib.common import get_target_sns_topic_name

# this script is executed before CDK deploy, it prepares settings (e.g. replaces variable parts such as AWS account ID etc.)
# The script can be modified for any specific set of config files

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
    file_path = os.path.join(script_dir, "settings", "replacements.json")

    parser = argparse.ArgumentParser(description="Process some settings.")
    parser.add_argument("--account-id", required=True, type=str, help="main account-id")
    parser.add_argument("--stage-name", required=True, type=str, help="stage-name")
    parser.add_argument("--region", required=True, type=str, help="region")
    args = parser.parse_args()

    stage_name = args.stage_name

    replacements_dict = {
        "<<main_account_id>>": args.account_id,
        "<<stage_name>>": stage_name,
        "<<region>>": args.region,
        "<<target_topic_name>>": get_target_sns_topic_name(stage_name=stage_name),
    }

    update_replacements_file(file_path, replacements_dict)
    print(
        f"Replacements applied to replacements.json: {json.dumps(replacements_dict, indent=4)}"
    )


if __name__ == "__main__":
    main()

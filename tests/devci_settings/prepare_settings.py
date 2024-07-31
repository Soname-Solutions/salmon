import boto3
import json
import os

# this script is executed before CDK deploy, it prepares settings (e.g. replaces variable parts such as AWS account ID etc.)
# The script can be modified for any specific set of config files 

def get_aws_account_id():
    session = boto3.Session()
    sts_client = session.client('sts')
    response = sts_client.get_caller_identity()
    account_id = response['Account']
    return account_id

def read_replacements_file(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def update_replacements_file(file_path, aws_account_id):
    data = read_replacements_file(file_path)
    data["<<main_account_id>>"] = aws_account_id
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, 'replacements.json')

    aws_account_id = get_aws_account_id()
    update_replacements_file(file_path, aws_account_id)
    print(f"Updated replacements.json with AWS Account ID: {aws_account_id}")

if __name__ == "__main__":
    main()

import boto3
import json
import os

# this script is executed before CDK deploy, it prepares settings (e.g. replaces variable parts such as AWS account ID etc.)
# The script can be modified for any specific set of config files


class PrepareSettingsException(Exception):
    """Exception raised for errors encountered while preparing test settings."""

    pass


def get_aws_account_id():
    session = boto3.Session()
    sts_client = session.client("sts")
    response = sts_client.get_caller_identity()
    account_id = response["Account"]
    return account_id


def get_vpc_id():
    """Required for the deployment of Grafana stack"""
    session = boto3.Session()
    ec2_client = session.client("ec2")
    response = ec2_client.describe_vpcs(
        Filters=[{"Name": "isDefault", "Values": ["true"]}]
    )

    try:
        vpc_id = response["Vpcs"][0]["VpcId"]
        return vpc_id
    except Exception as ex:
        raise PrepareSettingsException(f"Error while getting default VPC ID: {str(ex)}")


def get_security_group_id(vpc_id):
    """Required for the deployment of Grafana stack"""
    session = boto3.Session()
    ec2_client = session.client("ec2")
    response = ec2_client.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc_id]}], GroupNames=["default"]
    )

    try:
        security_group_id = response["SecurityGroups"][0]["GroupId"]
        return security_group_id
    except Exception as ex:
        raise PrepareSettingsException(
            f"Error while getting default security group ID: {str(ex)}"
        )


def read_replacements_file(file_path):
    with open(file_path, "r") as file:
        data = json.load(file)
    return data


def update_replacements_file(file_path, aws_account_id, vpc_id, security_group_id):
    data = read_replacements_file(file_path)
    data["<<main_account_id>>"] = aws_account_id
    data["<<grafana_vpc_id>>"] = vpc_id
    data["<<grafana_security_group_id>>"] = security_group_id

    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "settings", "replacements.json")

    aws_account_id = get_aws_account_id()
    vpc_id = get_vpc_id()
    security_group_id = get_security_group_id(vpc_id)
    update_replacements_file(file_path, aws_account_id, vpc_id, security_group_id)
    print(f"Updated replacements.json with AWS Account ID: {aws_account_id}")


if __name__ == "__main__":
    main()

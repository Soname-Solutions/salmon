import os
import json
import logging

from lib.core import json_utils as ju
from lib.core.constants import SettingConfigs

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GRAFANA_DASHBOARD_TEMPLATE_FOLDER = os.path.join("stacks", "grafana")


def generate_cloudwatch_dashboard_model(
    cloudwatch_log_group_name: str, cloudwatch_log_group_arn: str, account_id: str
) -> dict:
    """
    Generates Dashboard json model for CloudWatch Log Group.

    Args:
        cloudwatch_log_group_name (str): Alerts Events Log Group name in CloudWatch.
        cloudwatch_log_group_arn (str): ARN of Alerts Events Log Group in CloudWatch.
        account_id (str): Account ID.

    Returns:
        dashboard_data (dict): Dashboard json model.
    """
    dashboard_path = os.path.join(
        GRAFANA_DASHBOARD_TEMPLATE_FOLDER, "cloudwatch_dashboard.template.json"
    )
    with open(dashboard_path) as json_file:
        json_data = json.load(json_file)

    replacements = {
        "<<LOG_GROUP_NAME>>": cloudwatch_log_group_name,
        "<<LOG_GROUP_ARN>>": cloudwatch_log_group_arn,
        "<<ACCOUNT_ID>>": account_id,
        "<<RESOURCE_TYPES_STR>>": ",".join(SettingConfigs.RESOURCE_TYPES),
    }
    dashboard_data = ju.replace_values_in_json(json_data, replacements)

    return dashboard_data


def generate_timestream_dashboard_model(
    resource_type: str, timestream_database_name: str, timestream_table_name: str
) -> dict:
    """
    Generates Dashboard json model for Timestream table.

    Args:
        timestream_database_name (str): Timestream database name.
        timestream_table_name (str): Timestream table name.

    Returns:
        dashboard_data (dict): Dashboard json model.
    """
    dashboard_path = os.path.join(
        GRAFANA_DASHBOARD_TEMPLATE_FOLDER, f"{resource_type}_dashboard.template.json"
    )
    try:
        with open(dashboard_path) as json_file:
            json_data = json.load(json_file)
    except FileNotFoundError:
        logger.warning(
            f"Dashboard file for {resource_type} not found: {dashboard_path}. Skipping."
        )
        return None

    replacements = {
        "<<DATABASE_NAME>>": f'"{timestream_database_name}"',
        "<<DATABASE_TABLE>>": f'"{timestream_table_name}"',
    }
    dashboard_data = ju.replace_values_in_json(json_data, replacements)

    return dashboard_data


def generate_datasources_config(region: str, timestream_database_name: str) -> dict:
    """
    Generates Timestream and CloudWatch Datasources provisioning config file.

    Args:
        region (str): Region name.
        timestream_database_name (str):Timestream Database name.

    Returns:
        dict: Datasources provisioning config.
    """
    return {
        "apiVersion": 1,
        "datasources": [
            {
                "name": "Amazon-Timestream",
                "type": "grafana-timestream-datasource",
                "isDefault": False,
                "jsonData": {
                    "authType": "default",
                    "defaultRegion": region,
                    "defaultDatabase": f'"{timestream_database_name}"',
                },
            },
            {
                "name": "Cloudwatch",
                "type": "cloudwatch",
                "isDefault": False,
                "jsonData": {
                    "authType": "default",
                    "defaultRegion": region,
                },
            },
        ],
    }


def generate_dashboards_config(resource_types: list) -> dict:
    """
    Generates Dashboards provisioning config file.

    Args:
        resource_types (list): List of Resource types.

    Returns:
        dashboards_config (dict): Dashboards provisioning config.
    """
    dashboards_sections = []
    for resource_type in resource_types:
        dashboard_path = os.path.join(
            GRAFANA_DASHBOARD_TEMPLATE_FOLDER,
            f"{resource_type}_dashboard.template.json",
        )
        if os.path.exists(dashboard_path):
            dashboard_section = {
                "name": f"{resource_type}_dashboard",
                "folder": "Default SALMON Dashboards",
                "type": "file",
                "allowUiUpdates": True,
                "updateIntervalSeconds": 30,
                "options": {"path": f"data/{resource_type}_dashboard.json"},
            }
            dashboards_sections.append(dashboard_section)

    cw_dashboard_section = {
        "name": "cw_dashboard",
        "folder": "Default SALMON Dashboards",
        "type": "file",
        "allowUiUpdates": True,
        "updateIntervalSeconds": 30,
        "options": {"path": "data/cloudwatch_dashboard.json"},
    }
    dashboards_sections.append(cw_dashboard_section)
    dashboards_config = {"apiVersion": 1, "providers": dashboards_sections}

    return dashboards_config


def generate_user_data_script(
    region: str, settings_bucket_name: str, grafana_admin_secret_name: str
) -> str:
    """
    Generates User Data script that should be run at Grafana launch.

    Args:
        region (str): Region name.
        settings_bucket_name (str): Settings S3 Bucket name.
        grafana_admin_secret_name (str): Grafana Secret name.

    Returns:
        user_data_content (str): User data with set of commands.
    """
    user_data_file_path = os.path.join(
        GRAFANA_DASHBOARD_TEMPLATE_FOLDER, "grafana_user_data.template.sh"
    )
    with open(user_data_file_path, "r") as user_data_file:
        user_data_content = user_data_file.read()

    replacements = {
        "{region}": region,
        "{settings_bucket_name}": settings_bucket_name,
        "{grafana_admin_secret_name}": grafana_admin_secret_name,
    }

    for placeholder, replacement in replacements.items():
        user_data_content = user_data_content.replace(placeholder, replacement)

    return user_data_content

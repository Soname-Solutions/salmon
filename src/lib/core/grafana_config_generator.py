import os
import json


def generate_dashboard_model(
    service, timestream_database_name, timestream_table_name
) -> dict:
    """Generates Dashboard json model for each Service"""
    dashboard_path = os.path.join(
        "infra_tooling_account", "grafana", "sample_dashboard.json"
    )
    with open(dashboard_path) as json_file:
        dashboard_data = json.load(json_file)

    dashboard_data["title"] = f"Metrics Dashboard for {service}"
    dashboard_data["panels"][0]["datasource"] = f"Amazon-Timestream-{service}"
    dashboard_data["panels"][0]["title"] = f"{service}"
    dashboard_data["panels"][0]["targets"][0][
        "datasource"
    ] = f"Amazon-Timestream-{service}"
    dashboard_data["panels"][0]["targets"][0][
        "database"
    ] = f'"{timestream_database_name}"'
    dashboard_data["panels"][0]["targets"][0]["table"] = f'"{timestream_table_name}"'

    return dashboard_data


def generate_datasources_config_section(
    service, region, timestream_database_name, timestream_table_name
) -> dict:
    """Generates Datasource config section for each Service"""
    return {
        "name": f"Amazon-Timestream-{service}",
        "type": "grafana-timestream-datasource",
        "isDefault": False,
        "jsonData": {
            "authType": "default",
            "defaultRegion": region,
            "defaultDatabase": f'"{timestream_database_name}"',
            "defaultTable": f'"{timestream_table_name}"',
        },
    }


def generate_dashboards_config_section(service) -> dict:
    """Generates Dashboard config section for each Service"""
    return {
        "name": f"{service}_dashboard",
        "type": "file",
        "allowUiUpdates": True,
        "updateIntervalSeconds": 30,
        "options": {"path": f"data/{service}_dashboard.json"},
    }


def generate_user_data_script(
    region: str, settings_bucket_name: str, grafana_admin_secret_name: str
) -> str:
    """Generates User Data script that should be run at Grafana launch.

    Args:
        settings_bucket_name (str): Settings S3 Bucket name
        grafana_admin_secret_name (str): Grafana Secret name

    Returns:
        str: User data with set of commands
    """
    user_data_file_path = os.path.join(
        "infra_tooling_account", "grafana", "sample_user_data.sh"
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

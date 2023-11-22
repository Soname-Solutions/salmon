#!/usr/bin/env python3
import os
import sys

import aws_cdk as cdk

sys.path.append("../src")
from infra_monitored_account.infra_monitored_stack import InfraMonitoredStack

from lib.core import file_manager
from lib.core.constants import SettingFileNames
from lib.settings.settings_reader import (
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)
from lib.settings import settings_validator


def read_settings():
    settings_files_path = "../config/settings"
    general_file = file_manager.read_file(
        os.path.join(settings_files_path, SettingFileNames.GENERAL_FILE_NAME)
    )
    monitoring_groups_file = file_manager.read_file(
        os.path.join(settings_files_path, SettingFileNames.MONITORING_GROUPS_FILE_NAME)
    )
    recipients_file = file_manager.read_file(
        os.path.join(settings_files_path, SettingFileNames.RECIPIENTS_FILE_NAME)
    )

    general_settings_reader = GeneralSettingsReader(
        SettingFileNames.GENERAL_FILE_NAME, general_file
    )
    monitoring_groups_settings_reader = MonitoringSettingsReader(
        SettingFileNames.MONITORING_GROUPS_FILE_NAME, monitoring_groups_file
    )
    recipients_settings_reader = RecipientsSettingsReader(
        SettingFileNames.RECIPIENTS_FILE_NAME, recipients_file
    )

    settings_validator.validate(
        general_settings_reader,
        monitoring_groups_settings_reader,
        recipients_settings_reader,
    )

    return (
        general_settings_reader,
        monitoring_groups_settings_reader,
        recipients_settings_reader,
    )


if "STAGE_NAME" in os.environ:
    pass
else:
    exec('raise ValueError("Environment variable STAGE_NAME is undefined")')
STAGE_NAME = os.environ["STAGE_NAME"]

PROJECT_NAME = "salmon"

(
    general_settings_reader,
    monitoring_groups_settings_reader,
    recipients_settings_reader,
) = read_settings()

app = cdk.App()
InfraMonitoredStack(
    app,
    f"cf-{PROJECT_NAME}-InfraMonitoredStack-{STAGE_NAME}",
    tags={"project_name": PROJECT_NAME, "stage_name": STAGE_NAME},
    project_name=PROJECT_NAME,
    stage_name=STAGE_NAME,
    general_settings_reader=general_settings_reader,
)

app.synth()

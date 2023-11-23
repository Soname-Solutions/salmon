import os
from ...core import file_manager
from ...core.constants import SettingFileNames
from ..settings_reader import (
    GeneralSettingsReader,
    MonitoringSettingsReader,
    RecipientsSettingsReader,
)
from . import settings_validator


class LocalFileSystemSettingsProvider:

    """Class that provides a bundled functionality to read all settings files from the local filesystem and to validate them

    Attributes:
        general_settings_reader (GeneralSettingsReader): General Settings
        monitoring_groups_settings_reader (MonitoringSettingsReader): Monitoring Groups Settings
        recipients_settings_reader (RecipientsSettingsReader): Recipients Settings

    Methods:
        __read_settings: Reads settings from the initialized file path and saves the content
        validate_settings: Validates the saved settings
    """

    def __init__(self, settings_files_path: str):
        """Initializes settings readers accepting the path to the files as a string.

        Args:
            settings_files_path (str): Path to settings files in the local file system

        """
        (
            self._general_settings_reader,
            self._monitoring_groups_settings_reader,
            self._recipients_settings_reader,
        ) = self.__read_settings(settings_files_path)

    @property
    def general_settings_reader(self) -> GeneralSettingsReader:
        return self._general_settings_reader

    @property
    def monitoring_groups_settings_reader(self) -> MonitoringSettingsReader:
        return self._monitoring_groups_settings_reader

    @property
    def recipients_settings_reader(self) -> RecipientsSettingsReader:
        return self._recipients_settings_reader

    def __read_settings(self, settings_files_path: str):
        """Reads the settings from the provided local filesystem path, producing reader objects as the result

        Args:
            settings_files_path (str): Path to settings files in the local file system

        Returns:
            (GeneralSettingsReader, MonitoringSettingsReader, RecipientsSettingsReader): Reader objects which can access file content
        """
        general_file = file_manager.read_file(
            os.path.join(settings_files_path, SettingFileNames.GENERAL_FILE_NAME)
        )
        monitoring_groups_file = file_manager.read_file(
            os.path.join(
                settings_files_path, SettingFileNames.MONITORING_GROUPS_FILE_NAME
            )
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

        return (
            general_settings_reader,
            monitoring_groups_settings_reader,
            recipients_settings_reader,
        )

    def validate_settings(self):
        """Validates files content saved in the class object attributes"""
        settings_validator.validate(
            self.general_settings_reader,
            self.monitoring_groups_settings_reader,
            self.recipients_settings_reader,
        )

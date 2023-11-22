from fnmatch import fnmatch

from .settings_reader import SettingsReader
from lib.core.constants import Settings


class MonitoringSettingsReader(SettingsReader):
    """Represents a reader for Monitoring settings stored in JSON format.

    This class extends the SettingsReader to provide access to Monitoring settings from a JSON file.

    Attributes:
        monitoring_groups (dict): Dictionary of monitoring groups.

    Methods:
        get_monitoring_groups: Retrieves the list of monitoring groups.
        get_monitoring_groups_by_resource_name: Retrieves monitoring groups based on resource name.

    """

    def __init__(self, settings_file_name: str, settings_data: str):
        """MonitoringSettingsReader class constructor.

        Args:
            settings_file_name (str): The name of the Monitoring settings file.
            settings_data (str): The content of the Monitoring settings file in JSON format.
        """
        super().__init__(settings_file_name, settings_data)
        self._monitoring_groups = self.get_setting("monitoring_groups")

    @property
    def monitoring_groups(self) -> dict:
        """Property to get the monitoring groups."""
        return self._monitoring_groups

    def get_monitoring_group_names(self) -> list[str]:
        """Retrieves the Monitoring Group names from the Monitoring settings.

        Returns:
            list: List of Monitoring Group names.
        """
        return [m_grp.get("group_name") for m_grp in self._monitoring_groups]

    def get_monitored_environment_names(self) -> list[str]:
        """Retrieves the monitored_environment_names from the Monitoring settings.

        Returns:
            list: List of monitored_environment_names.
        """
        resource_groups = []
        for group in self._monitoring_groups:
            for monitored_resource in Settings.MONITORED_RESOURCES:
                resource_groups.extend(group.get(monitored_resource, []))

        return [res.get("monitored_environment_name") for res in resource_groups]

    def get_monitoring_groups_by_resource_names(self, resources: str) -> list[str]:
        """Retrieves monitoring groups based on resource names.

        Args:
            resources (list): The resource names to match against monitoring groups.

        Returns:
            list : List of matched monitoring group names.
        """
        matched_groups = set()  # Prevent duplicates

        for group in self._monitoring_groups:
            resource_groups = []
            for monitored_resource in Settings.MONITORED_RESOURCES:
                resource_groups += group.get(monitored_resource, [])

            for resource in resources:
                matched_groups.update(
                    group.get("group_name")
                    for res in resource_groups
                    if res.get("name") and fnmatch(resource, res.get("name"))
                )

        return list(matched_groups)

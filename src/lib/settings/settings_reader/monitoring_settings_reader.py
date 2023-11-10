from fnmatch import fnmatch

from .settings_reader import SettingsReader


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
        self.monitoring_groups = self.get_setting("monitoring_groups")

    def get_monitoring_groups(self) -> dict:
        """Retrieves the monitoring groups from the Monitoring settings.

        Returns:
            dict: Dictionary of monitoring groups.
        """
        return self.monitoring_groups

    def get_monitoring_groups_by_resource_names(self, resources: str) -> list[str]:
        """Retrieves monitoring groups based on resource names.

        Args:
            resources (list[str]): The resource names to match against monitoring groups.

        Returns:
            list[str] : List of matched monitoring group names.
        """
        matched_groups = set()  # Prevent duplicates

        for group in self.monitoring_groups:
            glue_jobs = group.get("glue_jobs", [])
            lambda_functions = group.get("lambda_functions", [])

            for resource in resources:
                matched_groups.update(
                    group.get("group_name")
                    for job in glue_jobs
                    if job.get("name") and fnmatch(resource, job.get("name"))
                )
                matched_groups.update(
                    group.get("group_name")
                    for function in lambda_functions
                    if function.get("name") and fnmatch(resource, function.get("name"))
                )

        return list(matched_groups)

import pytest
from src.settings.settings_reader import MonitoringSettingsReader


class TestMonitoringSettingsReader:
    @pytest.fixture(scope="class")
    def monitoring_settings_data(self):
        return """
        {
            "monitoring_groups": [
                {
                    "group_name": "Group1",
                    "glue_jobs": [{"name": "job1"}, {"name": "job2"}],
                    "lambda_functions": [{"name": "function1"}]
                },
                {
                    "group_name": "Group2",
                    "glue_jobs": [{"name": "job3"}, {"name": "job4"}],
                    "lambda_functions": [{"name": "function2"}]
                },
                {
                    "group_name": "Group1_intersected",
                    "glue_jobs": [{"name": "job5"}, {"name": "job6"}],
                    "lambda_functions": [{"name": "function2"}]
                },
                {
                    "group_name": "Group2_intersected",
                    "glue_jobs": [{"name": "job6"}, {"name": "job7"}],
                    "lambda_functions": [{"name": "function3"}]
                },
                {
                    "group_name": "Group1_wildcard",
                    "glue_jobs": [{"name": "job*"}],
                    "lambda_functions": [{"name": "function3"}]
                },
                {
                    "group_name": "Group2_wildcard",
                    "glue_jobs": [{"name": "*"}],
                    "lambda_functions": [{"name": "function3"}]
                }
            ]
        }
        """

    @pytest.fixture(scope="class")
    def monitoring_groups_data(self):
        return [
            {
                "group_name": "Group1",
                "glue_jobs": [{"name": "job1"}, {"name": "job2"}],
                "lambda_functions": [{"name": "function1"}],
            },
            {
                "group_name": "Group2",
                "glue_jobs": [{"name": "job3"}, {"name": "job4"}],
                "lambda_functions": [{"name": "function2"}],
            },
            {
                "group_name": "Group1_intersected",
                "glue_jobs": [{"name": "job5"}, {"name": "job6"}],
                "lambda_functions": [{"name": "function2"}],
            },
            {
                "group_name": "Group2_intersected",
                "glue_jobs": [{"name": "job6"}, {"name": "job7"}],
                "lambda_functions": [{"name": "function3"}],
            },
            {
                "group_name": "Group1_wildcard",
                "glue_jobs": [{"name": "job*"}],
                "lambda_functions": [{"name": "function3"}],
            },
            {
                "group_name": "Group2_wildcard",
                "glue_jobs": [{"name": "*"}],
                "lambda_functions": [{"name": "function3"}],
            },
        ]

    @pytest.fixture(scope="class")
    def monitoring_settings_reader(self, monitoring_settings_data):
        return MonitoringSettingsReader(
            "monitoring_groups.json", monitoring_settings_data
        )

    def test_get_monitoring_groups(
        self, monitoring_settings_reader, monitoring_groups_data
    ):
        monitoring_groups = monitoring_settings_reader.get_monitoring_groups()
        assert monitoring_groups == monitoring_groups_data

    def test_get_monitoring_groups_by_resource_names(self, monitoring_settings_reader):
        resources = ["job1", "function2"]
        matched_groups = (
            monitoring_settings_reader.get_monitoring_groups_by_resource_names(
                resources
            )
        )
        assert sorted(matched_groups) == [
            "Group1",
            "Group1_intersected",
            "Group1_wildcard",
            "Group2",
            "Group2_wildcard",
        ]

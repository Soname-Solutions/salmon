from datetime import datetime
from lib.digest_service import DigestMessageBuilder, SummaryEntry, AggregatedEntry
from lib.core.constants import (
    SettingConfigResourceTypes as types,
    DigestSettings,
    SettingConfigs,
)

START_TIME = datetime(2000, 1, 1, 0, 0, 0)
END_TIME = datetime(2000, 1, 2, 0, 0, 0)
DIGEST_DATA = [
    {
        "monitoring_group_1": {
            types.LAMBDA_FUNCTIONS: {
                "runs": {
                    "lambda-test": AggregatedEntry(
                        Status=DigestSettings.STATUS_OK,
                        Executions=2,
                        Success=2,
                        Errors=0,
                        Warnings=0,
                        Comments=[],
                        InsufficientRuns=False,
                        HasSLABreach=False,
                        HasFailedAttempts=False,
                    )
                },
                "summary": SummaryEntry(
                    Status=DigestSettings.STATUS_OK,
                    Executions=2,
                    Success=2,
                    Failures=0,
                    Warnings=0,
                ),
            }
        }
    },
    {
        "monitoring_group_2": {
            types.GLUE_JOBS: {
                "runs": {
                    "glue-test": AggregatedEntry(
                        Status=DigestSettings.STATUS_ERROR,
                        Executions=1,
                        Success=0,
                        Errors=1,
                        Warnings=0,
                        Comments=["Test Comment"],
                        InsufficientRuns=False,
                        HasSLABreach=False,
                        HasFailedAttempts=False,
                    )
                },
                "summary": SummaryEntry(
                    Status=DigestSettings.STATUS_ERROR,
                    Executions=1,
                    Success=0,
                    Failures=1,
                    Warnings=0,
                ),
            }
        }
    },
]


def test_message_builder_get_summary_table():
    expected_summary_table = {
        "table": {
            "header": {
                "values": [
                    "Monitoring Group",
                    "Service",
                    "Executions",
                    "Success",
                    "Failures",
                    "Warnings",
                ]
            },
            "rows": [
                {
                    "values": [
                        "monitoring_group_1",
                        SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES[
                            types.LAMBDA_FUNCTIONS
                        ],
                        2,
                        2,
                        0,
                        0,
                    ],
                    "style": DigestSettings.STATUS_OK,
                },
                {
                    "values": [
                        "monitoring_group_2",
                        SettingConfigs.RESOURCE_TYPE_DECORATED_NAMES[types.GLUE_JOBS],
                        1,
                        0,
                        1,
                        0,
                    ],
                    "style": DigestSettings.STATUS_ERROR,
                },
            ],
        }
    }
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA)
    returned_summary_table = message_builder._get_summary_table()

    assert len(returned_summary_table["table"]["rows"]) == len(
        DIGEST_DATA
    ), "For each Digest Data item, a row in summary table should be created"

    assert returned_summary_table == expected_summary_table


def test_message_builder_get_resource_table():
    runs_data = {
        "glue-test": AggregatedEntry(
            Status=DigestSettings.STATUS_OK,
            Executions=10,
            Success=10,
            Errors=0,
            Warnings=0,
            Comments=[],
            InsufficientRuns=False,
            HasSLABreach=False,
            HasFailedAttempts=False,
        )
    }
    expected_resource_table = {
        "table": {
            "header": {
                "values": ["Resource Name", "Success", "Errors", "Warnings", "Comments"]
            },
            "rows": [
                {
                    "values": ["glue-test", 10, 0, 0, ""],
                    "style": DigestSettings.STATUS_OK,
                }
            ],
        }
    }
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA)
    returned_resource_table = message_builder._get_resource_table(runs_data=runs_data)

    assert returned_resource_table == expected_resource_table


def test_generate_message_body_contains_summary_message():
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA)
    returned_message_body = message_builder.generate_message_body(
        digest_start_time=START_TIME, digest_end_time=END_TIME
    )

    summary_message_count = sum(
        1
        for item in returned_message_body
        if item.get("text")
        == (
            "This report has been generated for the period "
            "from January 01, 2000 12:00 AM to January 02, 2000 12:00 AM."
        )
    )

    assert summary_message_count == 1, "There should be exactly one summary message"


def test_generate_message_body_contains_all_sections():
    expected_section_names = {
        "Digest Summary",
        "monitoring_group_1: Lambda Functions",
        "monitoring_group_2: Glue Jobs",
    }
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA)
    returned_message_body = message_builder.generate_message_body(
        digest_start_time=START_TIME, digest_end_time=END_TIME
    )

    returned_section_counts = {}
    for item in returned_message_body:
        if "text" in item and item["style"] == "header":
            returned_section_counts[item["text"]] = (
                returned_section_counts.get(item["text"], 0) + 1
            )

    assert len(returned_section_counts) == len(
        expected_section_names
    ), "Not all expected sections were found"

    assert all(
        value == 1 for value in returned_section_counts.values()
    ), "There should be exactly one section for Digest Summary and each <group: resource type> pair"


def test_generate_message_body_сontains_all_tables():
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA)
    returned_message_body = message_builder.generate_message_body(
        digest_start_time=START_TIME, digest_end_time=END_TIME
    )

    for idx, item in enumerate(returned_message_body):
        if "text" in item and item["style"] == "header":
            if item["text"] == "Digest Summary":
                # For Digest Summary header, a table follows the digest summary message
                next_table_item = returned_message_body[idx + 2]
            else:
                next_table_item = returned_message_body[idx + 1]

            assert (
                "table" in next_table_item
            ), f"No table found after header '{item['text']}'"

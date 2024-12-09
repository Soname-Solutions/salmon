from datetime import datetime
from lib.digest_service import (
    DigestMessageBuilder,
    SummaryEntry,
    AggregatedEntry,
    GlueCatalogAggregatedEntry,
    GlueCatalogSummaryEntry,
)
from lib.core.constants import (
    SettingConfigResourceTypes as types,
    DigestSettings,
)

START_TIME = datetime(2000, 1, 1, 0, 0, 0)
END_TIME = datetime(2000, 1, 2, 0, 0, 0)

###########################################################
# Test Lambda resource attributes

LAMBDA_AGG_ENTRY = AggregatedEntry(
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
LAMBDA_GROUP_NAME = "monitoring_group_1"
LAMBDA_TYPE = types.LAMBDA_FUNCTIONS
LAMBDA_NAME = "lambda-test"

###########################################################
# Test Glue job resource attributes

GLUE_JOB_AGG_ENTRY = AggregatedEntry(
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
GLUE_JOB_GROUP_NAME = "monitoring_group_2"
GLUE_JOB_TYPE = types.GLUE_JOBS
GLUE_JOB_NAME = "glue-job-test"

###########################################################
DIGEST_DATA_WITHOUT_GLUE_CATALOGS = [
    {
        LAMBDA_GROUP_NAME: {
            LAMBDA_TYPE: {
                "runs": {LAMBDA_NAME: LAMBDA_AGG_ENTRY},
                "summary": SummaryEntry(
                    ResourceType=LAMBDA_TYPE,
                    MonitoringGroup=LAMBDA_GROUP_NAME,
                    EntryList=[LAMBDA_AGG_ENTRY],
                ),
            }
        }
    },
    {
        GLUE_JOB_GROUP_NAME: {
            GLUE_JOB_TYPE: {
                "runs": {GLUE_JOB_NAME: GLUE_JOB_AGG_ENTRY},
                "summary": SummaryEntry(
                    ResourceType=GLUE_JOB_TYPE,
                    MonitoringGroup=GLUE_JOB_GROUP_NAME,
                    EntryList=[GLUE_JOB_AGG_ENTRY],
                ),
            }
        }
    },
]


def test_message_builder_get_summary_table():
    message_builder = DigestMessageBuilder(
        digest_data=DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    )
    _, summary_data = message_builder._categorize_summary_data()
    returned_summary_table = message_builder._create_generic_summary_table(
        summary_data
    )["table"]

    assert len(returned_summary_table["rows"]) == len(
        DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    ), "For each Digest Data item, a row in summary table should be created"

    assert (
        returned_summary_table["header"]["values"]
        == DigestMessageBuilder.SUMMARY_TABLE_HEADERS
    )


def test_message_builder_get_resource_table():
    runs_data = {GLUE_JOB_NAME: GLUE_JOB_AGG_ENTRY}
    message_builder = DigestMessageBuilder(
        digest_data=DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    )
    returned_resource_table = message_builder._create_generic_resource_table(
        runs_data=runs_data
    )["table"]
    assert (
        returned_resource_table["header"]["values"]
        == DigestMessageBuilder.BODY_TABLE_HEADERS
    )
    assert returned_resource_table["rows"] == [
        {
            "values": [GLUE_JOB_NAME, 0, 1, 0, "Test Comment"],
            "style": DigestSettings.STATUS_ERROR,
        }
    ]


def test_generate_message_body_contains_summary_message():
    message_builder = DigestMessageBuilder(
        digest_data=DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    )
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
    message_builder = DigestMessageBuilder(
        digest_data=DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    )
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
    message_builder = DigestMessageBuilder(
        digest_data=DIGEST_DATA_WITHOUT_GLUE_CATALOGS
    )
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


###########################################################
# Test Glue Catalog object attributes

GLUE_CATALOG_AGG_ENTRY = GlueCatalogAggregatedEntry(
    Tables=5, Partitions=2, Indexes=0, TablesAdded=2, PartitionsAdded=1, IndexesAdded=0
)
GLUE_CATALOG_GROUP_NAME = "monitoring_group_3"
GLUE_CATALOG_TYPE = types.GLUE_DATA_CATALOGS
GLUE_CATALOG_NAME = "glue-catalog-test"


###########################################################
DIGEST_DATA_WITH_GLUE_CATALOGS = [
    {
        LAMBDA_GROUP_NAME: {
            LAMBDA_TYPE: {
                "runs": {LAMBDA_NAME: LAMBDA_AGG_ENTRY},
                "summary": SummaryEntry(
                    ResourceType=LAMBDA_TYPE,
                    MonitoringGroup=LAMBDA_GROUP_NAME,
                    EntryList=[LAMBDA_AGG_ENTRY],
                ),
            }
        }
    },
    {
        GLUE_JOB_GROUP_NAME: {
            GLUE_JOB_TYPE: {
                "runs": {GLUE_JOB_NAME: GLUE_JOB_AGG_ENTRY},
                "summary": SummaryEntry(
                    ResourceType=GLUE_JOB_TYPE,
                    MonitoringGroup=GLUE_JOB_GROUP_NAME,
                    EntryList=[GLUE_JOB_AGG_ENTRY],
                ),
            }
        }
    },
    {
        GLUE_CATALOG_GROUP_NAME: {
            GLUE_CATALOG_TYPE: {
                "runs": {GLUE_CATALOG_NAME: GLUE_CATALOG_AGG_ENTRY},
                "summary": GlueCatalogSummaryEntry(
                    ResourceType=GLUE_CATALOG_TYPE,
                    MonitoringGroup=GLUE_CATALOG_GROUP_NAME,
                    EntryList=[GLUE_CATALOG_AGG_ENTRY],
                ),
            }
        }
    },
]


def test_message_builder_with_glue_catalogs():
    expected_result = [
        {"text": "Digest Summary", "style": DigestMessageBuilder.HEADER_STYLE},
        {
            "text": "This report has been generated for the period from January 01, 2000 12:00 AM to January 02, 2000 12:00 AM.",
            "style": DigestMessageBuilder.TEXT_STYLE,
        },
        # first summary table for all resource types except Glue Data Catalogs
        {
            "table": {
                "header": {"values": DigestMessageBuilder.SUMMARY_TABLE_HEADERS},
                "rows": [
                    {
                        "values": [
                            "monitoring_group_1",
                            "Lambda Functions",
                            2,
                            2,
                            0,
                            0,
                        ],
                        "style": DigestSettings.STATUS_OK,
                    },
                    {
                        "values": ["monitoring_group_2", "Glue Jobs", 1, 0, 1, 0],
                        "style": DigestSettings.STATUS_ERROR,
                    },
                ],
            }
        },
        # second summary table for Glue Data Catalogs
        {
            "table": {
                "header": {
                    "values": DigestMessageBuilder.GLUE_CATALOG_SUMMARY_TABLE_HEADERS
                },
                "rows": [
                    {
                        "values": [
                            "monitoring_group_3",
                            "Glue Data Catalogs",
                            2,
                            1,
                            0,
                            5,
                            2,
                            0,
                        ],
                        "style": DigestSettings.NO_STATUS,
                    }
                ],
            }
        },
        # Group: Resource type specific table for each group: resource type pair
        # Group 1
        {
            "text": "monitoring_group_1: Lambda Functions",
            "style": DigestMessageBuilder.HEADER_STYLE,
        },
        {
            "table": {
                "header": {"values": DigestMessageBuilder.BODY_TABLE_HEADERS},
                "rows": [
                    {
                        "values": ["lambda-test", 2, 0, 0, ""],
                        "style": DigestSettings.STATUS_OK,
                    }
                ],
            }
        },
        # Group 2
        {
            "text": "monitoring_group_2: Glue Jobs",
            "style": DigestMessageBuilder.HEADER_STYLE,
        },
        {
            "table": {
                "header": {"values": DigestMessageBuilder.BODY_TABLE_HEADERS},
                "rows": [
                    {
                        "values": ["glue-job-test", 0, 1, 0, "Test Comment"],
                        "style": DigestSettings.STATUS_ERROR,
                    }
                ],
            }
        },
        # Group 3
        {
            "text": "monitoring_group_3: Glue Data Catalogs",
            "style": DigestMessageBuilder.HEADER_STYLE,
        },
        {
            "table": {
                "header": {
                    "values": DigestMessageBuilder.GLUE_CATALOG_BODY_TABLE_HEADERS
                },
                "rows": [
                    {
                        "values": ["glue-catalog-test", 2, 1, 0, 5, 2, 0, ""],
                        "style": DigestSettings.NO_STATUS,
                    }
                ],
            }
        },
    ]
    message_builder = DigestMessageBuilder(digest_data=DIGEST_DATA_WITH_GLUE_CATALOGS)

    response = message_builder.generate_message_body(
        digest_start_time=START_TIME, digest_end_time=END_TIME
    )

    assert response == expected_result

from abc import ABC, abstractmethod
from lib.settings import Settings
from lib.core.constants import SettingConfigResourceTypes as types, EventResult
from lib.event_mapper.resource_type_resolver import ResourceTypeResolver


class EventParsingException(Exception):
    pass


class GeneralAwsEventMapper(ABC):
    """Abstract class containing common logic to map AWS events to notification messages.

    Attributes:
        settings(Settings): Settings object

    Methods:
        to_notification_messages(dict): maps AWS event object to a list of notification message objects
    """

    def __init__(self, resource_type: str, event: dict, settings: Settings):
        self.resource_type = resource_type
        self.event = event
        self.monitored_env_name = settings.get_monitored_environment_name(
            event["account"], event["region"]
        )

    @abstractmethod
    def get_resource_name(self) -> str:
        """Returns name of the AWS resource the given event belongs to (job/stateMachine/function etc.)

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_event_result(self) -> str:
        """Returns the result of the occurred event

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_execution_info_url(self, resource_name: str) -> str:
        """Returns the url of the occurred event

        Args:
            event (dict): Event object
            resource_name (str): Resource name
        """
        pass

    @abstractmethod
    def get_resource_state(self) -> str:
        """Returns the state of the resource according to the event

        Args:
            event (dict): Event object
        """
        pass

    @abstractmethod
    def get_message_body(self) -> list[dict]:
        """Returns composed message body for the given AWS event

        Args:
            event (dict): Event object
        """
        pass

    def __get_message_subject(self) -> str:
        """Return message subject based on the event

        Args:
            event (dict): Event object

        Returns:
            str: Message subject
        """
        resource_name = self.get_resource_name()
        resource_state = self.get_resource_state()
        resource_type = ResourceTypeResolver.resolve(self.event)
        return f"{self.monitored_env_name}: {resource_state} - {resource_type} : {resource_name}"

    def create_message_body_with_common_rows(self) -> tuple[list, list]:
        message_body = []
        table = {}
        rows = []
        table["table"] = {}
        table["table"]["rows"] = rows
        message_body.append(table)

        # todo: when completing task for event -> self.event, also override this method for glue workflows
        rows.append(self.create_table_row(["AWS Account", self.event["account"]]))
        rows.append(self.create_table_row(["AWS Region", self.event["region"]]))
        rows.append(self.create_table_row(["Time", self.event["time"]]))
        rows.append(self.create_table_row(["Event Type", self.event["detail-type"]]))

        return message_body, rows

    def get_row_style(self) -> str:
        return "error" if self.get_event_result() == EventResult.FAILURE else None

    def create_table_row(self, values: list, style: str = None) -> dict:
        """Returns prepared table row for given values and style

        Args:
            values (list): List of values to put in columns
            style (str, optional): Style to apply to the row. Defaults to None.

        Returns:
            dict: Row object
        """
        row = {"values": values}
        if style is not None:
            row["style"] = style
        return row

    def to_message(self) -> dict:
        """Maps AWS event object to a message object structure

        Args:
            event (dict): Event object

        Returns:
            dict: Message to be sent as a notification
        """
        message = {
            "message_subject": self.__get_message_subject(),
            "message_body": self.get_message_body(),
        }

        return message


class CustomAwsEventMapper(GeneralAwsEventMapper):
    """Intermediate class providing custom implementation for create_message_body_with_common_rows.

    Attributes:
        Inherits attributes from GeneralAwsEventMapper.

    Methods:
        create_message_body_with_common_rows(self) -> tuple[list, list]: Overrides the method in
        GeneralAwsEventMapper to provide a custom implementation for creating message body with common rows.
    """

    def create_message_body_with_common_rows(self) -> tuple[list, list]:
        message_body = []
        table = {}
        rows = []
        table["table"] = {}
        table["table"]["rows"] = rows
        message_body.append(table)

        rows.append(
            self.create_table_row(
                ["AWS Account", self.event["detail"]["origin_account"]]
            )
        )
        rows.append(
            self.create_table_row(["AWS Region", self.event["detail"]["origin_region"]])
        )
        rows.append(self.create_table_row(["Time", self.event["time"]]))
        rows.append(self.create_table_row(["Event Type", self.event["detail-type"]]))

        return message_body, rows


class ExecutionInfoUrlMixin:
    @staticmethod
    def get_url(
        resource_type: str,
        region_name: str,
        resource_name: str,
        account_id: str = None,
        run_id: str = None,
    ) -> str:
        """Returns the link to the particular resource run."""
        url_mapping = {
            types.GLUE_JOBS: f"https://{region_name}.console.aws.amazon.com/gluestudio/home?region={region_name}#/job/{resource_name}/run/{run_id}",
            types.STEP_FUNCTIONS: f"https://{region_name}.console.aws.amazon.com/states/home?region={region_name}#/v2/executions/details/arn:aws:states:{region_name}:{account_id}:execution:{resource_name}:{run_id}",
            types.LAMBDA_FUNCTIONS: f"https://{region_name}.console.aws.amazon.com/cloudwatch/home?region={region_name}#logsV2:log-groups/log-group/$252Faws$252Flambda$252F{resource_name}/log-events/",
            types.GLUE_CRAWLERS: f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/data-catalog/crawlers/view/{resource_name}",
            types.GLUE_WORKFLOWS: f"https://{region_name}.console.aws.amazon.com/glue/home?region={region_name}#/v2/etl-configuration/workflows/run/{resource_name}?runId={run_id}",
        }
        return url_mapping.get(resource_type, "")

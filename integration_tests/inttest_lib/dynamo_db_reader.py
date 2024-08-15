import json
import boto3
from dataclasses import dataclass

@dataclass
class IntegrationTestMessage:
    MessageId: str
    Subject: str
    MessageBody: str
    SentTimestamp: int

class DynamoDBReaderException(Exception):
    """Exception raised for errors encountered while reading messages from Dynamo DB."""

    pass

class DynamoDBReader:
    def __init__(self, table_name: str, dynamodb_client=None):
        self.table_name = table_name
        self.dynamodb_client = dynamodb_client if dynamodb_client else boto3.client('dynamodb')

    def get_all_messages(self) -> list[IntegrationTestMessage]:
        response = self.dynamodb_client.scan(TableName=self.table_name)

        # Extract messages from the response and convert them to IntegrationTestMessage objects
        messages = []
        for item in response['Items']:
            message = IntegrationTestMessage(
                MessageId=item['MessageId']['S'],
                Subject=item['Subject']['S'],
                MessageBody=item['MessageBody']['S'],
                SentTimestamp=int(item['Timestamp']['N'])
            )
            messages.append(message)

        return messages
      
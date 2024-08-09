import json
import boto3
from dataclasses import dataclass

@dataclass
class SqsMessage:
    MessageId: str
    Subject: str
    MessageBody: str
    SentTimestamp: int

class SQSQueueReaderException(Exception):
    """Exception raised for errors encountered while reading messages to the SQS queue."""

    pass

class SQSQueueReader:
    @classmethod
    def get_queue_url_from_name(cls, queue_name: str, region_name: str) -> str:
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()["Account"]       
        queue_url = f'https://sqs.{region_name}.amazonaws.com/{account_id}/{queue_name}'
        return queue_url

    def __init__(self, queue_url: str, sqs_client=None):
        self.queue_url = queue_url
        self.sqs_client = sqs_client if sqs_client else boto3.client('sqs')

    def get_all_messages(self) -> list[SqsMessage]:
        outp = []
        while True:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=10,  
                MessageAttributeNames=['All'],
                AttributeNames=['All'],
                VisibilityTimeout=1 # So we can safely retrieve multiple times in case it's needed
            )

            messages = response.get('Messages', [])
            if not messages:
                break              
            
            for msg in messages:                
                message_id = msg.get('MessageId',"")
                receipt_handle = msg.get('ReceiptHandle',"")                
                print(message_id)
                body = json.loads(msg.get('Body', ""))
                subject = body.get('Subject', {})
                message_body = body.get('MessageBody', '')
                sent_timestamp = int(msg.get('Attributes', {}).get('SentTimestamp', ''))

                outp.append(
                    SqsMessage(MessageId=message_id,
                               Subject=subject, 
                               MessageBody=message_body, 
                               SentTimestamp=sent_timestamp
                               )
                )

        return outp        


     
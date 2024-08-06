import os
import sys
from inttest_lib.sqs_queue_reader import SqsMessage, SQSQueueReader

from inttest_lib.time_helper import epoch_to_utc_string

queue_name = "queue-salmon-inttest-target-devit.fifo"

queue_url = SQSQueueReader.get_queue_url_from_name(queue_name, "eu-central-1")

reader = SQSQueueReader(queue_url)

messages: list[SqsMessage] = reader.get_all_messages()

for message in messages:
    print(message.MessageId, message.SentTimestamp, message.Subject)
    print(epoch_to_utc_string(message.SentTimestamp))
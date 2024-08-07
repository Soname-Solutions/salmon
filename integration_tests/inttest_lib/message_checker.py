
from inttest_lib.sqs_queue_reader import SqsMessage

class MessagesChecker:
    def __init__(self, messages: list[SqsMessage]):
        self.messages: list[SqsMessage] = messages

    def subject_contains_all(self, filters: list[str]):
        """
            Filters out message where subject contains all required values    
        """
        outp = []
        for msg in self.messages:
            if all(f in msg.Subject for f in filters):
                outp.append(msg)
        return outp

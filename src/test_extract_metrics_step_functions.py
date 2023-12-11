import boto3
import json
from pydantic import BaseModel

from datetime import datetime
from typing import Optional

#####################################

class Execution(BaseModel):
    executionArn: str
    stateMachineArn: str
    name: str
    status: str
    startDate: datetime
    stopDate: datetime

    @property
    def duration(self):
        return self.stopDate - self.startDate

class HTTPHeaders(BaseModel):
    x_amzn_requestid: Optional[str] = None
    date: str
    content_type: Optional[str] = None
    content_length: Optional[str] = None
    connection: str

class ResponseMetadata(BaseModel):
    RequestId: str
    HTTPStatusCode: int
    HTTPHeaders: HTTPHeaders
    RetryAttempts: int

class ExecutionsData(BaseModel):
    executions: list[Execution]
    nextToken: Optional[str] = None
    ResponseMetadata: ResponseMetadata

#####################################

def get_stepfunction_arn(sfn_client, stepfunction_name):    
    response = sfn_client.list_state_machines()
    for statemachine in response['stateMachines']:
        if statemachine['name'] == stepfunction_name:
            return statemachine['stateMachineArn']
    return None

def stepfun_handler(event, context):

    step_function_name = "stepfunction-salmonts-sample-dev"
    sfn_client = boto3.client('stepfunctions')

    step_function_arn = get_stepfunction_arn(sfn_client, step_function_name)
    
    # gets all step function executions
    response = sfn_client.list_executions(
        stateMachineArn=step_function_arn,
        maxResults=10)
    
    # output = json.dumps(response, indent=4, default=str)
    # print(output)
    # exit(0)
    
    executions_data = ExecutionsData(**response)
    
    #print(executions_data)
    #print(executions_data.model_dump_json(indent=4))

    # duration
    for execution in executions_data.executions:
        print(execution.name, execution.status, execution.duration)



    


if __name__ == "__main__":
    stepfun_handler(None, None)    
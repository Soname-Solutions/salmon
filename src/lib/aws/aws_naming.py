class AWSNaming:
    @classmethod
    def __get_project_and_stage(cls, stack_obj: object):
        # Check if project_name and stage_name attributes exist in stack_obj
        if hasattr(stack_obj, "project_name") and hasattr(stack_obj, "stage_name"):
            return stack_obj.project_name, stack_obj.stage_name
        else:
            raise AttributeError(
                "stack_obj is missing 'project_name' or 'stage_name' attributes"
            )

    @classmethod
    def __resource_name_with_check(
        cls, stack_obj: object, prefix: str, meaning: str
    ) -> str:
        project_name, stage_name = AWSNaming.__get_project_and_stage(stack_obj)

        outp = f"{prefix}-{project_name}-{meaning}-{stage_name}"

        return outp

    @classmethod
    def CfnOutput(cls, stack_obj: object, meaning: str) -> str:
        prefix = "output"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)
    
    @classmethod
    def DynamoDBTable(cls, stack_obj: object, meaning: str) -> str:
        prefix = "dyntbl"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def EventBus(cls, stack_obj: object, meaning: str) -> str:
        prefix = "eventbus"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def EventBusRule(cls, stack_obj: object, meaning: str) -> str:
        prefix = "eventbusrule"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)
    
    @classmethod
    def GlueJob(cls, stack_obj: object, meaning: str) -> str:
        prefix = "glue"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def IAMPolicy(cls, stack_obj: object, meaning: str) -> str:
        prefix = "policy"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def IAMRole(cls, stack_obj: object, meaning: str) -> str:
        prefix = "role"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def KMSKey(cls, stack_obj: object, meaning: str) -> str:
        prefix = "key"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def LambdaFunction(cls, stack_obj: object, meaning: str) -> str:
        prefix = "lambda"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def S3Bucket(cls, stack_obj: object, meaning: str) -> str:
        prefix = "s3"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def SNSTopic(cls, stack_obj: object, meaning: str) -> str:
        prefix = "topic"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def SQSQueue(cls, stack_obj: object, meaning: str) -> str:
        prefix = "queue"
        ending = ".fifo" # FIFO queue names must end in '.fifo'
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning) + ending

    @classmethod
    def TimestreamDB(cls, stack_obj: object, meaning: str) -> str:
        prefix = "timestream"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def TimestreamTable(cls, stack_obj: object, meaning: str) -> str:
        prefix = "tstable"
        outp = f"{prefix}-{meaning}"  # Table lives inside DB, so we identify project and stage names by DB
        return outp

    @classmethod
    def TimestreamMetricsTable(cls, stack_obj: object, resource_type: str) -> str:
        ###
        meaning = f"{resource_type}-metrics"
        return AWSNaming.TimestreamTable(stack_obj, meaning)

    @classmethod
    def EC2(cls, stack_obj: object, meaning: str) -> str:
        prefix = "ec2"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def Secret(cls, stack_obj: object, meaning: str) -> str:
        prefix = "secret"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def LogGroupName(cls, stack_obj: object, meaning: str) -> str:
        prefix = "log-group"
        outp = AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)
        return outp

    @classmethod
    def LogStreamName(cls, stack_obj: object, meaning: str) -> str:
        prefix = "log-stream"
        outp = AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)
        return outp

    @classmethod
    def Arn_IAMRole(cls, stack_obj: object, account_id: str, role_name: str) -> str:
        return f"arn:aws:iam::{account_id}:role/{role_name}"

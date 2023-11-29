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

        # todo: if name longer than XX symbols (90? - AWS Limit) - throw an error

        return outp

    @classmethod
    def CfnOutput(cls, stack_obj: object, meaning: str) -> str:
        prefix = "output"
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
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def TimestreamDB(cls, stack_obj: object, meaning: str) -> str:
        prefix = "timestream"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

    @classmethod
    def TimestreamTable(cls, stack_obj: object, meaning: str) -> str:
        prefix = "tstable"
        return AWSNaming.__resource_name_with_check(stack_obj, prefix, meaning)

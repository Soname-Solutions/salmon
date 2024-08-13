import json

from aws_cdk import (
    Stack,
    Tags,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class GitHubActionsResourcesStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        iam_user = iam.User(
            self,
            "GithubActionsServiceUser",
            user_name="github-actions-service-user",
        )

        access_key = iam.CfnAccessKey(
            self, "GithubActionsUserAccessKey", user_name=iam_user.user_name
        )

        # Store the credentials in Secrets Manager
        secret = secretsmanager.Secret(
            self,
            "GithubActionsUserSecret",
            secret_name="secret/salmon/github-actions-service-user",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "AccessKeyId": access_key.ref,
                        "SecretAccessKey": access_key.attr_secret_access_key,
                    }
                ),
                generate_string_key="dummy",
            ),
        )

        # Attach policies to the IAM user
        self.attach_assume_role_policy(iam_user)
        self.attach_glue_job_runner_policy(iam_user)
        self.attach_lambda_runner_policy(iam_user)
        self.attach_sqs_queue_reader_policy(iam_user)
        self.attach_timestream_query_runner_policy(iam_user)

    def attach_assume_role_policy(self, iam_user):
        # Permissions needed to CDK deploy/destroy
        assume_role_policy = iam.Policy(
            self,
            "AssumeRolePolicy",
            policy_name="AssumeRolePolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["sts:AssumeRole"],
                    resources=[
                        "arn:aws:iam::*:role/cdk-*-deploy-role-*",
                        "arn:aws:iam::*:role/cdk-*-file-publishing-role-*",
                    ],
                )
            ],
        )
        iam_user.attach_inline_policy(assume_role_policy)

    def attach_glue_job_runner_policy(self, iam_user):
        # Policy for Integration Tests (Glue Jobs)
        glue_policy = iam.Policy(
            self,
            "GlueJobRunnerPolicy",
            policy_name="GlueJobRunnerPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:StartJobRun",
                        "glue:GetJobRun",
                        "glue:GetJob",
                        "glue:ListJobs",
                    ],
                    resources=["*"],  # todo: restrict to specific resources
                )
            ],
        )
        iam_user.attach_inline_policy(glue_policy)

    def attach_lambda_runner_policy(self, iam_user):
        # Policy for Integration Tests (Lambda Functions)
        lambda_runner_policy = iam.Policy(
            self,
            "LambdaRunnerPolicy",
            policy_name="LambdaRunnerPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        # Lambda actions
                        "lambda:InvokeFunction",
                        # CloudWatch Logs actions
                        "logs:FilterLogEvents",
                        "logs:GetLogEvents",
                        "logs:StartQuery",
                        "logs:GetQueryResults",
                        "logs:DescribeLogGroups",
                    ],
                    resources=["*"],  # todo: restrict to specific resources
                )
            ],
        )
        iam_user.attach_inline_policy(lambda_runner_policy)

    def attach_sqs_queue_reader_policy(self, iam_user):
        sqs_queue_reader_policy = iam.Policy(
            self,
            "SqsQueueReaderPolicy",
            policy_name="SqsQueueReaderPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        # SQS actions
                        "sqs:ReceiveMessage",
                        "sqs:GetQueueAttributes",
                        "sqs:ListQueues",  # Optional
                        "sqs:GetQueueUrl",
                        # STS actions
                        "sts:GetCallerIdentity",
                    ],
                    resources=["*"],  # todo: restrict to specific resources
                )
            ],
        )
        iam_user.attach_inline_policy(sqs_queue_reader_policy)

    def attach_timestream_query_runner_policy(self, iam_user):
        timestream_query_runner_policy = iam.Policy(
            self,
            "TimestreamQueryRunnerPolicy",
            policy_name="TimestreamQueryRunnerPolicy",
            statements=[
                iam.PolicyStatement(
                    actions=[
                        # Timestream query actions
                        "timestream:Select",
                        "timestream:DescribeTable",
                        "timestream:ListMeasures",
                        "timestream:DescribeEndpoints",  # align with tooling stack - separate statement
                        "kms:Decrypt",
                    ],
                    resources=["*"],  # todo: restrict to specific resources
                )
            ],
        )
        iam_user.attach_inline_policy(timestream_query_runner_policy)

import json

from aws_cdk import (
    Stack,
    Tags,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from lib.aws.aws_naming import AWSNaming


class GitHubActionsResourcesStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        self.project_name = kwargs.pop("project_name", None)
        self.stage_name = kwargs.pop("stage_name", None)
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
        self.attach_glue_dq_runner_policy(iam_user)
        self.attach_glue_workflow_runner_policy(iam_user)
        self.attach_step_function_runner_policy(iam_user)
        self.attach_lambda_runner_policy(iam_user)
        self.attach_emr_serverless_runner_policy(iam_user)
        self.attach_dynamodb_reader_policy(iam_user)
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
            users=[iam_user],
        )

    def attach_glue_job_runner_policy(self, iam_user):
        # Policy for Integration Tests (Glue Jobs)
        glue_policy = iam.ManagedPolicy(
            self,
            "GlueJobRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "GlueJobRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:StartJobRun",
                        "glue:GetJobRun",
                        "glue:GetJob",
                        "glue:ListJobs",
                    ],
                    resources=["arn:aws:glue:*:*:job/*salmon*"],
                )
            ],
            users=[iam_user],
        )

    def attach_glue_workflow_runner_policy(self, iam_user):
        # Policy for Integration Tests (Glue Workflows)
        glue_workflow_policy = iam.ManagedPolicy(
            self,
            "GlueWorkflowRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "GlueWorkflowRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:StartWorkflowRun",
                        "glue:GetWorkflowRun",
                        "glue:GetWorkflow",
                        "glue:ListWorkflows",
                    ],
                    resources=["arn:aws:glue:*:*:workflow/*salmon*"],
                )
            ],
            users=[iam_user],
        )

    def attach_step_function_runner_policy(self, iam_user):
        # Policy for Integration Tests (Step Functions)
        step_function_policy = iam.ManagedPolicy(
            self,
            "StepFunctionRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "StepFunctionRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=["states:StartExecution", "states:ListExecutions"],
                    resources=["arn:aws:states:*:*:stateMachine:*salmon*"],
                ),
                iam.PolicyStatement(
                    actions=["states:DescribeExecution"],
                    resources=["arn:aws:states:*:*:execution:*salmon*"],
                ),
                iam.PolicyStatement(
                    actions=["states:ListStateMachines"],
                    resources=["*"],
                ),
            ],
            users=[iam_user],
        )

    def attach_emr_serverless_runner_policy(self, iam_user):
        # Policy for Integration Tests (EMR Serverless)
        step_function_policy = iam.ManagedPolicy(
            self,
            "EMRServerlessRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "EMRServerlessRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "emr-serverless:StartJobRun",
                        "emr-serverless:GetJobRun",
                        "emr-serverless:ListJobRuns",
                        "emr-serverless:CancelJobRun",
                    ],
                    # can't filter by application_name, because policy allows only application_id, which is unusable
                    resources=["*"],
                    # limiting scope by requiring tag "salmon"
                    conditions={
                        "StringLike": {f"aws:ResourceTag/{self.project_name}": "*"}
                    },
                ),
                iam.PolicyStatement(
                    actions=[
                        "emr-serverless:ListApplications",
                        "emr-serverless:TagResource",
                    ],
                    resources=["*"],
                ),
            ],
            users=[iam_user],
        )

    def attach_glue_dq_runner_policy(self, iam_user):
        # Policy for Integration Tests (Glue Data Quality)
        glue_dq_policy = iam.ManagedPolicy(
            self,
            "GlueDQRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "GlueDQRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:StartDataQualityRulesetEvaluationRun",
                        "glue:GetDataQualityResult",
                    ],
                    resources=["arn:aws:glue:*:*:dataQualityRuleset/*salmon*"],
                ),
                iam.PolicyStatement(
                    actions=["glue:ListDataQualityResults"],
                    resources=[
                        "arn:aws:glue:*:*:dataQualityRuleset/*"
                    ],  # '*' is required, can't limit to *salmon*
                ),
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=["arn:aws:iam::*:role/*salmon*"],
                ),
                iam.PolicyStatement(
                    actions=["glue:GetTable"],
                    resources=[
                        "arn:aws:glue:*:*:catalog",
                        "arn:aws:glue:*:*:database/*salmon*",
                        "arn:aws:glue:*:*:table/*/*salmon*",
                    ],
                ),
            ],
            users=[iam_user],
        )

    def attach_lambda_runner_policy(self, iam_user):
        # Policy for Integration Tests (Lambda Functions)
        lambda_runner_policy = iam.ManagedPolicy(
            self,
            "LambdaRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "LambdaRunnerPolicy"),
            statements=[
                # Lambda actions
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=["arn:aws:lambda:*:*:function:*salmon*"],
                ),
                # CloudWatch Logs actions
                iam.PolicyStatement(
                    actions=[
                        "logs:FilterLogEvents",
                        "logs:GetLogEvents",
                        "logs:StartQuery",
                        "logs:GetQueryResults",
                        "logs:DescribeLogGroups",
                    ],
                    resources=["arn:aws:logs:*:*:log-group:*salmon*"],
                ),
            ],
            users=[iam_user],
        )

    def attach_timestream_query_runner_policy(self, iam_user):
        timestream_query_runner_policy = iam.ManagedPolicy(
            self,
            "TimestreamQueryRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(
                self, "TimestreamQueryRunnerPolicy"
            ),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        # Timestream query actions
                        "timestream:Select",
                        "timestream:DescribeTable",
                        "timestream:ListMeasures",
                        "kms:Decrypt",
                    ],
                    resources=["arn:aws:timestream:*:*:database/*salmon*/table/*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        # This should refer to "*" (AWS limitations)
                        "timestream:DescribeEndpoints",
                    ],
                    resources=["*"],
                ),
                iam.PolicyStatement(
                    actions=[
                        "kms:Decrypt",
                    ],
                    resources=["*"],
                    conditions={  # Restriction is implemented on KMS key alias level
                        "ForAnyValue:StringLike": {
                            "kms:ResourceAliases": "alias/*salmon*"
                        }
                    },
                ),
            ],
            users=[iam_user],
        )

    def attach_dynamodb_reader_policy(self, iam_user):
        # Policy for reading from DynamoDB
        dynamodb_reader_policy = iam.ManagedPolicy(
            self,
            "DynamoDBReaderPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "DynamoDBReaderPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "dynamodb:Scan",
                    ],
                    resources=[
                        "arn:aws:dynamodb:*:*:table/*salmon*",
                    ],
                )
            ],
            users=[iam_user],
        )

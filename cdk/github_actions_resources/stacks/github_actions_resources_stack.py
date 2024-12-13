import json

from aws_cdk import (
    Stack,
    Tags,
    Fn,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct

from lib.aws.aws_naming import AWSNaming
from lib.git.git_helper import get_owner_and_repo_name


class GitHubActionsResourcesStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        self.project_name = kwargs.pop("project_name", None)
        self.stage_name = kwargs.pop("stage_name", None)
        super().__init__(scope, id, **kwargs)

        # Create OpenID provider and role for GitHub actions to assume
        github_actions_role = self.create_github_oidc_role()

        # Create IAM user
        # Note: IAM service role makes IAM user obsolete for running workflows
        # It's decided to keep IAM user, as it's the easiest way to run tests locally
        # with permissions identical to github workflows
        iam_user = self.create_github_service_user()

        # Collect all policies
        policies = [
            self.create_assume_role_policy(),
            self.create_ec2_role_policy(),
            self.create_glue_job_runner_policy(),
            self.create_glue_dq_runner_policy(),
            self.create_glue_workflow_runner_policy(),
            self.create_glue_catalog_runner_policy(),
            self.create_glue_crawler_runner_policy(),
            self.create_step_function_runner_policy(),
            self.create_lambda_runner_policy(),
            self.create_emr_serverless_runner_policy(),
            self.create_dynamodb_reader_policy(),
            self.create_timestream_query_runner_policy(),
        ]

        # Attach policies to both IAM user and role
        self.assign_to_principals(
            policies, users=[iam_user], roles=[github_actions_role]
        )

    def assign_to_principals(
        self,
        policies: list[iam.Policy],
        users: list[iam.User],
        roles: list[iam.Role],
    ):
        for policy in policies:
            for user in users:
                policy.attach_to_user(user)
            for role in roles:
                policy.attach_to_role(role)

    def create_github_service_user(self) -> iam.User:
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

        return iam_user

    def create_github_oidc_role(self) -> iam.Role:
        # Define the OIDC provider for GitHub
        oidc_provider_url = "https://token.actions.githubusercontent.com"
        client_id = "sts.amazonaws.com"

        repo_owner, repo_name = get_owner_and_repo_name()

        oidc_provider = iam.OpenIdConnectProvider(
            self, "GitHubOIDCProvider", url=oidc_provider_url, client_ids=[client_id]
        )

        # Define the GitHub Actions role with limited S3 access
        github_actions_role = iam.Role(
            self,
            "GitHubActionsRole",
            assumed_by=iam.WebIdentityPrincipal(
                oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": f"repo:{repo_owner}/{repo_name}:*"
                    },
                },
            ),  # type: ignore
            role_name="salmon-github-tests-service-role",
        )

        # Attach the S3 read-only policy
        github_actions_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")
        )

        return github_actions_role

    def create_assume_role_policy(self) -> iam.Policy:
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
                        "arn:aws:iam::*:role/cdk-*-lookup-role-*",
                        "arn:aws:iam::*:role/cdk-*-file-publishing-role-*",
                    ],
                )
            ],
        )
        return assume_role_policy

    def create_ec2_role_policy(self) -> iam.Policy:
        # Permissions needed to CDK deploy/destroy of Grafana stack
        ec2_role_policy = iam.Policy(
            self,
            "EC2RolePolicy",
            policy_name="EC2RolePolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2:DescribeVpcs",
                        "ec2:DescribeSecurityGroups",
                        "ec2:DescribeImages",
                        "ec2:DescribeSubnets",
                        "ec2:DescribeRouteTables",
                        "ec2:DescribeVpnGateways",
                    ],
                    resources=["*"],
                )
            ],
        )
        return ec2_role_policy

    def create_glue_job_runner_policy(self) -> iam.ManagedPolicy:
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
        )
        return glue_policy

    def create_glue_workflow_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Glue Workflows)
        policy = iam.ManagedPolicy(
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
        )
        return policy

    def create_glue_catalog_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Glue Data Catalogs)
        policy = iam.ManagedPolicy(
            self,
            "GlueCatalogRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "GlueCatalogRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:GetTable",
                        "glue:GetTables",
                        "glue:GetPartitions",
                        "glue:GetPartitionIndexes",
                    ],
                    resources=[
                        "arn:aws:glue:*:*:catalog",
                        "arn:aws:glue:*:*:database/*salmon*",
                        "arn:aws:glue:*:*:table/*/*salmon*",
                    ],
                )
            ],
        )
        policy.add_statements(
            iam.PolicyStatement(
                actions=[
                    "glue:CreatePartition",
                    "glue:CreatePartitionIndex",
                    "glue:DeleteTable",
                ],
                effect=iam.Effect.ALLOW,
                resources=["arn:aws:glue:*:*:table/*/*salmon*"],
            )
        )

        return policy

    def create_glue_crawler_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Glue Crawlers)
        policy = iam.ManagedPolicy(
            self,
            "GlueCrawlerRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "GlueCrawlerRunnerPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=[
                        "glue:StartCrawler",
                        "glue:GetCrawler",
                        "glue:ListCrawlers",
                        "glue:StopCrawler",
                    ],
                    resources=["arn:aws:glue:*:*:crawler/*salmon*"],
                ),
                iam.PolicyStatement(
                    actions=["glue:GetCrawlerMetrics"],
                    resources=["*"],  # the only way how GetCrawlerMetrics works
                ),
            ],
        )
        return policy

    def create_step_function_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Step Functions)
        policy = iam.ManagedPolicy(
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
        )
        return policy

    def create_emr_serverless_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (EMR Serverless)
        policy = iam.ManagedPolicy(
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
        )
        return policy

    def create_glue_dq_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Glue Data Quality)
        policy = iam.ManagedPolicy(
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
        )
        return policy

    def create_lambda_runner_policy(self) -> iam.ManagedPolicy:
        # Policy for Integration Tests (Lambda Functions)
        policy = iam.ManagedPolicy(
            self,
            "LambdaRunnerPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "LambdaRunnerPolicy"),
            statements=[
                # Lambda actions
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction", "lambda:GetFunction"],
                    resources=["arn:aws:lambda:*:*:function:*salmon*"],
                ),
                # CloudWatch Logs actions
                iam.PolicyStatement(
                    actions=[
                        "logs:FilterLogEvents",
                        "logs:GetLogEvents",
                        "logs:StartQuery",
                        "logs:GetQueryResults",
                        "logs:CreateLogGroup",
                    ],
                    resources=["arn:aws:logs:*:*:log-group:*salmon*"],
                ),
                # CloudWatch Logs actions
                iam.PolicyStatement(
                    actions=["logs:DescribeLogGroups"],
                    resources=["*"],
                ),
            ],
        )
        return policy

    def create_timestream_query_runner_policy(self) -> iam.ManagedPolicy:
        policy = iam.ManagedPolicy(
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
                    actions=["kms:Decrypt"],
                    resources=["*"],
                    conditions={  # Restriction is implemented on KMS key alias level
                        "ForAnyValue:StringLike": {
                            "kms:ResourceAliases": "alias/*salmon*"
                        }
                    },
                ),
            ],
        )
        return policy

    def create_dynamodb_reader_policy(self) -> iam.ManagedPolicy:
        # Policy for reading from DynamoDB
        policy = iam.ManagedPolicy(
            self,
            "DynamoDBReaderPolicy",
            managed_policy_name=AWSNaming.IAMPolicy(self, "DynamoDBReaderPolicy"),
            statements=[
                iam.PolicyStatement(
                    actions=["dynamodb:Scan"],
                    resources=[
                        "arn:aws:dynamodb:*:*:table/*salmon*",
                    ],
                )
            ],
        )
        return policy

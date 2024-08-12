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

        iam_user = iam.User(self, "GithubActionsServiceUser",
                            user_name="github-actions-service-user",
                            )
        
        access_key = iam.CfnAccessKey(self, "GithubActionsUserAccessKey",
                                      user_name=iam_user.user_name)

        # Store the credentials in Secrets Manager
        secret = secretsmanager.Secret(self, "GithubActionsUserSecret",
                                       secret_name="secret/salmon/github-actions-service-user",
                                       generate_secret_string=secretsmanager.SecretStringGenerator(
                                           secret_string_template=json.dumps({
                                               "AccessKeyId": access_key.ref,
                                               "SecretAccessKey": access_key.attr_secret_access_key,
                                           }),
                                           generate_string_key="dummy",
                                       ))
        
        assume_role_policy = iam.Policy(self, "AssumeRolePolicy",
                                        policy_name="AssumeRolePolicy",
                                        statements=[
                                            iam.PolicyStatement(
                                                effect=iam.Effect.ALLOW,
                                                actions=["sts:AssumeRole"],
                                                resources=[
                                                    "arn:aws:iam::*:role/cdk-*-deploy-role-*",
                                                    "arn:aws:iam::*:role/cdk-*-file-publishing-role-*"
                                                ]
                                            )
                                        ])
        iam_user.attach_inline_policy(assume_role_policy)  
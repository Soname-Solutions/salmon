# iam_helper.py
from aws_cdk import aws_iam as iam
from constructs import Construct


def create_glue_iam_role(scope: Construct, role_id: str, role_name: str) -> iam.Role:
    """
    Create an IAM role for AWS Glue with the necessary managed policies.

    Args:
        scope (Construct): The CDK construct that will own the new role, typically 'self' from a Stack.
        role_id (str): CloudFormation ID of the role.
        role_name (str): The name of the role.

    Returns:
        iam.Role: The created IAM role.
    """
    glue_iam_role = iam.Role(
        scope,
        role_id,
        assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
        role_name=role_name,
        managed_policies=[
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AWSGlueServiceRole"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess"),
        ],
    )
    return glue_iam_role

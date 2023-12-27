import yaml
import json
from aws_cdk import (
    Stack,
    CfnOutput,
    Fn,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct
from lib.aws.aws_naming import AWSNaming
from lib.settings.settings import Settings
from lib.core.constants import SettingConfigs
from lib.core.grafana_config_generator import (
    generate_dashboard_model,
    generate_datasources_config_section,
    generate_dashboards_config_section,
    generate_user_data_script,
)


class InfraToolingGrafanaStack(Stack):
    """
    This class represents a stack for Grafana instance in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the GrafanaStack.

        Args:
            scope (Construct): The CDK app or stack that this stack is a part of.
            construct_id (str): The identifier for this stack.
            **kwargs: Arbitrary keyword arguments. Specifically looks for:
                - project_name (str): The name of the project. Used for naming resources. Defaults to None.
                - stage_name (str): The name of the deployment stage. Used for naming resources. Defaults to None.
                - settings (Tuple): Tuple containing settings. Defaults to None.

        """
        self.stage_name = kwargs.pop("stage_name", None)
        self.project_name = kwargs.pop("project_name", None)
        self.settings: Settings = kwargs.pop("settings", None)

        super().__init__(scope, construct_id, **kwargs)

        (
            input_timestream_database_arn,
            input_timestream_kms_key_arn,
            input_settings_bucket_arn,
            settings_bucket,
        ) = self.get_common_stack_references()

        (
            grafana_vpc_id,
            grafana_security_group_id,
        ) = self.settings.get_grafana_mandatory_settings()

        (
            grafana_key_pair_name,
            grafana_bitnami_image,
            grafana_instance_type,
        ) = self.settings.get_grafana_optional_settings()

        (
            grafana_admin_secret_name,
            grafana_admin_secret_arn,
        ) = self.create_grafana_admin_secret()

        # Create Grafana key pair if not provided
        if not grafana_key_pair_name:
            grafana_key_pair_name = self.create_grafana_key_pair()

        self.prepare_and_upload_grafana_configuration_files(settings_bucket)

        grafana_instance = self.create_grafana_instance(
            grafana_vpc_id=grafana_vpc_id,
            grafana_security_group_id=grafana_security_group_id,
            input_timestream_kms_key_arn=input_timestream_kms_key_arn,
            input_timestream_database_arn=input_timestream_database_arn,
            input_settings_bucket_arn=input_settings_bucket_arn,
            grafana_admin_secret_name=grafana_admin_secret_name,
            grafana_admin_secret_arn=grafana_admin_secret_arn,
            grafana_bitnami_image=grafana_bitnami_image,
            grafana_key_pair_name=grafana_key_pair_name,
            grafana_instance_type=grafana_instance_type,
            settings_bucket_name=settings_bucket.bucket_name,
        )

        output_grafana_instance_public_ip = CfnOutput(
            self,
            "GrafanaPublicIp",
            value=grafana_instance.instance_public_ip,
            description="The Public IP of the Grafana Instance",
            # To sign in to Grafana, go to http://<grafana-instance-public-ip>:3000
            export_name=AWSNaming.CfnOutput(self, "grafana-instance-public-ip"),
        )

    def get_common_stack_references(self) -> tuple[str, str, str, s3.Bucket]:
        """
        Retrieves common stack references required for the stack's operations.
        These include the Timestream database ARN, Timestream KMS key ARN, settings S3 bucket and its ARN.

        Returns:
            tuple: A tuple containing references to the Timestream database ARN, Timestream KMS key ARN,
                   settings S3 bucket and its ARN.
        """

        input_timestream_database_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-storage-arn")
        )
        input_timestream_kms_key_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "metrics-events-kms-key-arn")
        )
        input_settings_bucket_arn = Fn.import_value(
            AWSNaming.CfnOutput(self, "settings-bucket-arn")
        )

        settings_bucket = s3.Bucket.from_bucket_arn(
            self,
            "salmonSettingsBucket",
            bucket_arn=input_settings_bucket_arn,
        )

        return (
            input_timestream_database_arn,
            input_timestream_kms_key_arn,
            input_settings_bucket_arn,
            settings_bucket,
        )

    def create_grafana_admin_secret(self) -> tuple[str, str]:
        """
        Creates Grafana admin password in Secrets Manager.

        Returns:
            tuple: A tuple containing Grafana admin secret name and its ARN
        """
        grafana_admin_secret = secretsmanager.Secret(
            self,
            "GrafanaSecret",
            secret_name=AWSNaming.SM(self, "grafana-secret"),
            description="Grafana secret stored in AWS Secrets Manager",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                include_space=False,
                generate_string_key="password",
                password_length=20,
                secret_string_template='{"username":"admin"}',
            ),
        )

        return grafana_admin_secret.secret_name, grafana_admin_secret.secret_arn

    def create_grafana_key_pair(self) -> str:
        """
        Creates Key Pair for Grafana instance.

        Returns:
            str: Key Pair name
        """
        grafana_key_pair = ec2.CfnKeyPair(
            self,
            "GrafanaKeyPair",
            key_name=AWSNaming.KMSKey(self, "grafana-key-pair"),
        )

        return grafana_key_pair.key_name

    def prepare_and_upload_grafana_configuration_files(self, settings_bucket) -> None:
        """
        Generates and uploads Grafana configuration files to S3 bucket.
        For each Service, a separate dashboard and data source will be provisioned.
        The files will be uploaded to settings/grafana dedicated folder.

        Args:
            settings_bucket (s3.Bucket): Settings S3 Bucket
        """
        metric_table_names = {x: f"{x}-metrics" for x in SettingConfigs.RESOURCE_TYPES}
        services = metric_table_names.keys()
        timestream_database_name = AWSNaming.TimestreamDB(
            self, "metrics-events-storage"
        )

        # Generate Dashboard JSON model for each Service
        for i, service in enumerate(services):
            timestream_table_name = AWSNaming.TimestreamTable(
                self, metric_table_names[service]
            )
            dashboard_data = generate_dashboard_model(
                service, timestream_database_name, timestream_table_name
            )

            # Upload to S3 settings/grafana/dashboards bucket
            s3deploy.BucketDeployment(
                self,
                f"GrafanaDashboardsDeployment{i}",
                sources=[
                    s3deploy.Source.data(
                        f"{service}_dashboard.json",
                        json.dumps(dashboard_data, sort_keys=False),
                    )
                ],
                destination_bucket=settings_bucket,
                destination_key_prefix="settings/grafana/dashboards",
                prune=False,
            )

        # Generate Data sources and Dashboards YAML config files
        datasources_sections = [
            generate_datasources_config_section(
                service=service,
                region=Stack.of(self).region,
                timestream_database_name=timestream_database_name,
                timestream_table_name=AWSNaming.TimestreamTable(
                    self, metric_table_names[service]
                ),
            )
            for service in services
        ]
        dashboards_sections = [
            generate_dashboards_config_section(service) for service in services
        ]
        datasources_config = {"apiVersion": 1, "datasources": datasources_sections}
        dashboards_config = {"apiVersion": 1, "providers": dashboards_sections}

        # Upload to S3 settings/grafana/conf bucket
        s3deploy.BucketDeployment(
            self,
            "GrafanaYamlConfigsDeployment",
            sources=[
                s3deploy.Source.data(
                    "datasources.yaml",
                    yaml.dump(
                        datasources_config, default_flow_style=False, sort_keys=False
                    ),
                ),
                s3deploy.Source.data(
                    "dashboards.yaml",
                    yaml.dump(
                        dashboards_config, default_flow_style=False, sort_keys=False
                    ),
                ),
            ],
            destination_bucket=settings_bucket,
            destination_key_prefix="settings/grafana/conf",
        )

    def create_grafana_instance(
        self,
        grafana_vpc_id: str,
        grafana_security_group_id: str,
        input_timestream_kms_key_arn: str,
        input_timestream_database_arn: str,
        input_settings_bucket_arn: str,
        grafana_admin_secret_arn: str,
        grafana_instance_type: str,
        grafana_bitnami_image: str,
        grafana_key_pair_name: str,
        settings_bucket_name: str,
        grafana_admin_secret_name: str,
    ) -> ec2.Instance:
        """Creates Grafana instance with the provisioned dashboards.

        Args:
            grafana_vpc_id (str): VPC ID for Grafana instance
            grafana_security_group_id (str): Security Group ID for Grafana instance
            input_timestream_kms_key_arn (str): ARN of Timestream KMS Key
            input_timestream_database_arn (str): ARN of Timestream DB
            input_settings_bucket_arn (str): ARN of Settings S3 Bucket
            grafana_admin_secret_arn (str): ARN of Grafana secret
            grafana_instance_type (str): Grafana Instance type
            grafana_image (str): Bitnami Grafana image from AWS Marketplace
            grafana_key_pair_name (str): Grafana Key Pair name
            settings_bucket_name (str): Settings S3 Bucket name
            grafana_admin_secret_name (str): Grafana secret name

        Returns:
            ec2.Instance: Grafana Instance
        """
        # Import the VPC, security group provided
        vpc = ec2.Vpc.from_lookup(self, "VpcImport", vpc_id=grafana_vpc_id)
        security_group = ec2.SecurityGroup.from_lookup_by_id(
            self, "SecurityGroupImport", security_group_id=grafana_security_group_id
        )

        # Create Grafana Role
        grafana_role = iam.Role(
            self,
            "GrafanaInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            description="Role assumed by Grafana instance",
            role_name=AWSNaming.IAMRole(self, "grafana-instance"),
        )

        grafana_role.add_to_policy(
            # to be able to decrypt data from Timestream DB
            iam.PolicyStatement(
                actions=["kms:Decrypt"],
                effect=iam.Effect.ALLOW,
                resources=[input_timestream_kms_key_arn],
            )
        )
        grafana_role.add_to_policy(
            # to be able to make Timestream API calls from Grafana instance
            iam.PolicyStatement(
                actions=[
                    "timestream:DescribeEndpoints",
                    "timestream:ListDatabases",
                    "timestream:SelectValues",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        )
        grafana_role.add_to_policy(
            # to be able to describe Timestream DB and list its tables
            iam.PolicyStatement(
                actions=["timestream:ListTables", "timestream:DescribeDatabase"],
                effect=iam.Effect.ALLOW,
                resources=[input_timestream_database_arn],
            )
        )
        grafana_role.add_to_policy(
            # to be able to read data from Timestream tables and list their measures
            iam.PolicyStatement(
                actions=[
                    "timestream:Select",
                    "timestream:ListMeasures",
                    "timestream:DescribeTable",
                ],
                effect=iam.Effect.ALLOW,
                resources=[f"{input_timestream_database_arn}/table/*"],
            )
        )
        grafana_role.add_to_policy(
            # to be able to list configuration files in S3 bucket
            iam.PolicyStatement(
                actions=["s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=[input_settings_bucket_arn],
            )
        )
        grafana_role.add_to_policy(
            # to be able to get configuration files from S3 bucket
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[f"{input_settings_bucket_arn}/*"],
            )
        )
        grafana_role.add_to_policy(
            # to be able to read Grafana admin password from Secrets Manager
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                effect=iam.Effect.ALLOW,
                resources=[grafana_admin_secret_arn],
            )
        )

        grafana_instance = ec2.Instance(
            self,
            "GrafanaInstance",
            instance_type=ec2.InstanceType(grafana_instance_type),
            machine_image=ec2.MachineImage.lookup(name=grafana_bitnami_image),
            vpc=vpc,
            instance_name=AWSNaming.EC2(self, "grafana-instance"),
            key_name=grafana_key_pair_name,
            role=grafana_role,
            security_group=security_group,
            user_data=ec2.UserData.custom(
                generate_user_data_script(
                    region=Stack.of(self).region,
                    settings_bucket_name=settings_bucket_name,
                    grafana_admin_secret_name=grafana_admin_secret_name,
                )
            ),
        )

        return grafana_instance

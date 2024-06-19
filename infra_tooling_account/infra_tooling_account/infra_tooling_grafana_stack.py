import yaml
import json
from aws_cdk import (
    NestedStack,
    CfnOutput,
    Fn,
    aws_s3 as s3,
    aws_iam as iam,
    aws_ec2 as ec2,
    aws_kms as kms,
    aws_s3_deployment as s3deploy,
    aws_secretsmanager as secretsmanager,
    aws_timestream as timestream,
    aws_logs as cloudwatch_logs,
)
from constructs import Construct
from lib.aws.aws_naming import AWSNaming
from lib.settings.settings import Settings
from lib.core.constants import SettingConfigs
from lib.core.grafana_config_generator import (
    generate_timestream_dashboard_model,
    generate_cloudwatch_dashboard_model,
    generate_datasources_config,
    generate_dashboards_config,
    generate_user_data_script,
)


class InfraToolingGrafanaStack(NestedStack):
    """
    This class represents a stack for Grafana instance in AWS CloudFormation.

    Attributes:
        stage_name (str): The stage name of the deployment, used for naming resources.
        project_name (str): The name of the project, used for naming resources.

    Methods:
        get_common_stack_references(): Retrieves references to artifacts created in common stack.
        get_grafana_settings(): Retrieves Grafana related settings.
        create_grafana_admin_secret(): Creates Grafana Admin Secret in Secrets Manager.
        create_grafana_key_pair(): Creates Grafana Key Pair.
        generate_grafana_configuration_files(): Generates Grafana provisioning config files and uploads to S3 bucket.
        create_grafana_instance(): Creates Grafana instance.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        settings_bucket: s3.Bucket,
        timestream_storage: timestream.CfnDatabase,
        timestream_kms_key: kms.Key,
        **kwargs,
    ) -> None:
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

        self.settings_bucket = settings_bucket
        input_settings_bucket_arn = self.settings_bucket.bucket_arn

        input_timestream_database_arn = timestream_storage.attr_arn
        input_timestream_kms_key_arn = timestream_kms_key.key_arn

        super().__init__(scope, construct_id, **kwargs)

        # passing log group through parameters didn't work, so defining it inside the code
        alert_events_log_group = cloudwatch_logs.LogGroup.from_log_group_name(
            self,
            "salmonAlertEventsLogGroup",
            log_group_name=AWSNaming.LogGroupName(self, "alert-events"),
        )        

        (
            grafana_vpc_id,
            grafana_security_group_id,
            grafana_key_pair_name,
            grafana_bitnami_image,
            grafana_instance_type,
        ) = self.settings.get_grafana_settings()

        (
            grafana_admin_secret_name,
            grafana_admin_secret_arn,
        ) = self.create_grafana_admin_secret()

        # Create Grafana key pair if not provided
        if not grafana_key_pair_name:
            grafana_key_pair_name = self.create_grafana_key_pair()

        self.generate_grafana_configuration_files(
            settings_bucket=settings_bucket,
            cloudwatch_log_group_arn=alert_events_log_group.log_group_arn,
            cloudwatch_log_group_name=alert_events_log_group.log_group_name,
        )

        grafana_instance = self.create_grafana_instance(
            grafana_vpc_id=grafana_vpc_id,
            grafana_security_group_id=grafana_security_group_id,
            timestream_kms_key_arn=input_timestream_kms_key_arn,
            timestream_database_arn=input_timestream_database_arn,
            settings_bucket_arn=input_settings_bucket_arn,
            alert_events_log_group_arn=alert_events_log_group.log_group_arn,
            grafana_admin_secret_name=grafana_admin_secret_name,
            grafana_admin_secret_arn=grafana_admin_secret_arn,
            grafana_bitnami_image=grafana_bitnami_image,
            grafana_key_pair_name=grafana_key_pair_name,
            grafana_instance_type=grafana_instance_type,
            settings_bucket_name=settings_bucket.bucket_name,
        )

        output_grafana_url = CfnOutput(
            self,
            "GrafanaURL",
            # To sign in to Grafana, go to http://<grafana-instance-public-ip>:3000
            value=f"http://{grafana_instance.instance_public_ip}:3000",
            description="Grafana URL",
            export_name=AWSNaming.CfnOutput(self, "grafana-url"),
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
            secret_name=AWSNaming.Secret(self, "grafana-password"),
            description="Grafana secret stored in AWS Secrets Manager",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_characters="-",
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
            grafana_key_pair_name (str): Key Pair name.
        """
        grafana_key_pair = ec2.CfnKeyPair(
            self,
            "GrafanaKeyPair",
            key_name=AWSNaming.KMSKey(self, "grafana-key-pair"),
        )

        return grafana_key_pair.key_name

    def generate_grafana_configuration_files(
        self,
        settings_bucket: s3.Bucket,
        cloudwatch_log_group_name: str,
        cloudwatch_log_group_arn: str,
    ) -> None:
        """
        Generates the following Grafana provisioning configuration files and uploads them to S3 bucket:
            - the dashboards for each Resource type based on the Timestream corresponding table
            - the dashboard based on the CloudWatch Alerts Events Log Stream
            - YAML provisioning config files with the data sources and dashboards

        Args:
            settings_bucket (s3.Bucket): Settings S3 Bucket.
            cloudwatch_log_group_name (str): Alerts Events Log Group name in CloudWatch.
            cloudwatch_log_group_arn (str): Alerts Events Log Group ARN in CloudWatch.
        """
        metric_table_names = {
            x: AWSNaming.TimestreamMetricsTable(None, x)
            for x in SettingConfigs.RESOURCE_TYPES
        }
        resource_types = metric_table_names.keys()
        timestream_database_name = AWSNaming.TimestreamDB(
            self, "metrics-events-storage"
        )

        # Generate Timestream Dashboard JSON model for each Resource type and upload to S3
        for i, resource_type in enumerate(resource_types):
            dashboard_data = generate_timestream_dashboard_model(
                resource_type=resource_type,
                timestream_database_name=timestream_database_name,
                timestream_table_name=metric_table_names[resource_type],
            )
            if dashboard_data:
                sources = [
                    s3deploy.Source.data(
                        f"{resource_type}_dashboard.json",
                        json.dumps(dashboard_data, sort_keys=False),
                    )
                ]
                self.upload_grafana_config_files_to_s3(
                    deployment_name=f"GrafanaTimestreamDashboardDeployment{i}",
                    sources=sources,
                    settings_bucket=settings_bucket,
                    destination_key_prefix="settings/grafana/dashboards",
                    prune_option=False,
                )

        # Generate CloudWatch Dashboard JSON model and upload to S3
        cw_dashboard_data = generate_cloudwatch_dashboard_model(
            cloudwatch_log_group_name=cloudwatch_log_group_name,
            cloudwatch_log_group_arn=cloudwatch_log_group_arn,
            account_id=NestedStack.of(self).account,
        )
        sources = [
            s3deploy.Source.data(
                "cloudwatch_dashboard.json",
                json.dumps(cw_dashboard_data, sort_keys=False),
            )
        ]
        self.upload_grafana_config_files_to_s3(
            deployment_name=f"GrafanaCloudWatchDashboardDeployment",
            sources=sources,
            settings_bucket=settings_bucket,
            destination_key_prefix="settings/grafana/dashboards",
            prune_option=False,
        )

        # Generate YAML provisioning config files and upload to S3
        datasources_config = generate_datasources_config(
            region=NestedStack.of(self).region,
            timestream_database_name=timestream_database_name,
        )
        dashboards_config = generate_dashboards_config(resource_types=resource_types)
        sources = [
            s3deploy.Source.data(
                "datasources.yaml",
                yaml.dump(
                    datasources_config, default_flow_style=False, sort_keys=False
                ),
            ),
            s3deploy.Source.data(
                "dashboards.yaml",
                yaml.dump(dashboards_config, default_flow_style=False, sort_keys=False),
            ),
        ]
        self.upload_grafana_config_files_to_s3(
            deployment_name="GrafanaYamlConfigsDeployment",
            sources=sources,
            settings_bucket=settings_bucket,
            destination_key_prefix="settings/grafana/conf",
            prune_option=True,
        )

    def upload_grafana_config_files_to_s3(
        self,
        deployment_name: str,
        sources: s3deploy.ISource,
        settings_bucket: s3.Bucket,
        destination_key_prefix: str,
        prune_option: bool,
    ) -> None:
        """
        Uploads Grafana configuration files to settings/grafana dedicated folder in S3 bucket.

        Args:
            deployment_name (str): The deployment name.
            sources (s3deploy.ISource): The sources from which to deploy the contents of this bucket.
            settings_bucket (s3.Bucket): Settings S3 Bucket.
            destination_key_prefix (str): Key prefix in the destination bucket.
            prune_option (bool): Prune option.
        """
        s3deploy.BucketDeployment(
            self,
            deployment_name,
            sources=sources,
            destination_bucket=settings_bucket,
            destination_key_prefix=destination_key_prefix,
            prune=prune_option,
        )

    def create_grafana_instance(
        self,
        grafana_vpc_id: str,
        grafana_security_group_id: str,
        timestream_kms_key_arn: str,
        timestream_database_arn: str,
        settings_bucket_arn: str,
        alert_events_log_group_arn: str,
        grafana_admin_secret_arn: str,
        grafana_instance_type: str,
        grafana_bitnami_image: str,
        grafana_key_pair_name: str,
        settings_bucket_name: str,
        grafana_admin_secret_name: str,
    ) -> ec2.Instance:
        """Creates Grafana instance with the provisioned dashboards and datasources.

        Args:
            grafana_vpc_id (str): VPC ID for Grafana instance
            grafana_security_group_id (str): Security Group ID for Grafana instance
            timestream_kms_key_arn (str): ARN of Timestream KMS Key
            timestream_database_arn (str): ARN of Timestream DB
            settings_bucket_arn (str): ARN of Settings S3 Bucket
            alert_events_log_group_arn (str): ARN of CloudWatch Log Group with Alert Events
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
                resources=[timestream_kms_key_arn],
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
                resources=[timestream_database_arn],
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
                resources=[f"{timestream_database_arn}/table/*"],
            )
        )
        grafana_role.add_to_policy(
            # to be able to list configuration files in S3 bucket
            iam.PolicyStatement(
                actions=["s3:ListBucket"],
                effect=iam.Effect.ALLOW,
                resources=[settings_bucket_arn],
            )
        )
        grafana_role.add_to_policy(
            # to be able to get configuration files from S3 bucket
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                effect=iam.Effect.ALLOW,
                resources=[f"{settings_bucket_arn}/*"],
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
        grafana_role.add_to_policy(
            # to be able to read CloudWatch logs
            iam.PolicyStatement(
                actions=[
                    "logs:Describe*",
                    "logs:Get*",
                    "logs:List*",
                    "logs:StartQuery",
                    "logs:StopQuery",
                    "logs:TestMetricFilter",
                    "logs:FilterLogEvents",
                ],
                effect=iam.Effect.ALLOW,
                resources=[alert_events_log_group_arn],
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
                    region=NestedStack.of(self).region,
                    settings_bucket_name=settings_bucket_name,
                    grafana_admin_secret_name=grafana_admin_secret_name,
                )
            ),
        )

        return grafana_instance

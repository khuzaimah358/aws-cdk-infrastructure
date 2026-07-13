import aws_cdk as cdk
from aws_cdk import (
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_ssm as ssm,
)
from constructs import Construct


class DatabaseStack(cdk.Stack):
    """
    TICKET-05: RDS PostgreSQL Database
    ────────────────────────────────────
    Managed PostgreSQL inside private VPC subnet.
    Multi-AZ in production for high availability.
    Credentials auto-generated and stored in Secrets Manager.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        vpc: ec2.Vpc,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        is_prod = environment == 'prod'

        # Instance size per environment
        instance_map = {
            'dev':     ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            'staging': ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.SMALL),
            'prod':    ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MEDIUM),
        }

        storage_map = {
            'dev':     20,
            'staging': 50,
            'prod':    100,
        }

        # ── RDS Instance ────────────────────────────────
        self.db_instance = rds.DatabaseInstance(
            self, 'Database',
            database_name='myappdb',
            instance_identifier=f'myapp-{environment}-db',

            # Engine: PostgreSQL 15
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15_3,
            ),

            # Size
            instance_type=instance_map[environment],

            # Network — PRIVATE subnet only!
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),

            # Storage
            allocated_storage=storage_map[environment],
            storage_type=rds.StorageType.GP3,
            storage_encrypted=True,

            # High Availability (multi-AZ only for prod)
            multi_az=is_prod,

            # Backups
            backup_retention=cdk.Duration.days(7 if is_prod else 1),
            delete_automated_backups=not is_prod,

            # Credentials (uses Secrets Manager auto-generation)
            credentials=rds.Credentials.from_generated_secret(
                username='dbadmin',
                secret_name=f'/myapp/{environment}/database/credentials',
            ),

            # Safety
            deletion_protection=is_prod,
            removal_policy=(
                cdk.RemovalPolicy.RETAIN
                if is_prod
                else cdk.RemovalPolicy.DESTROY
            ),
        )

        # ── Store DB endpoint in SSM (developers use this) ──
        ssm.StringParameter(
            self, 'DbHost',
            parameter_name=f'/myapp/{environment}/database/host',
            string_value=self.db_instance.db_instance_endpoint_address,
            description=f'RDS endpoint for {environment}',
        )

        ssm.StringParameter(
            self, 'DbName',
            parameter_name=f'/myapp/{environment}/database/name',
            string_value='myappdb',
            description='Database name',
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'DbEndpoint',
            value=self.db_instance.db_instance_endpoint_address,
            description=f'Database endpoint for {environment}',
            export_name=f'DbEndpoint-{environment}',
        )

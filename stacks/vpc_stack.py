import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class VpcStack(cdk.Stack):
    """
    TICKET-02: VPC & Networking
    ────────────────────────────
    Creates isolated private network:
      - 2 Public subnets  (API Gateway, NAT)
      - 2 Private subnets (Lambda, RDS — no direct internet)
      - NAT Gateway       (private resources reach internet outbound)
      - Security Groups   (Lambda, RDS, App)
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── VPC ────────────────────────────────────────
        self.vpc = ec2.Vpc(
            self, 'AppVpc',
            vpc_name=f'myapp-{environment}-vpc',
            max_azs=2,
            nat_gateways=1,   # 1 NAT saves cost (use 2 in prod)
            ip_addresses=ec2.IpAddresses.cidr('10.0.0.0/16'),
            subnet_configuration=[
                # Public — internet-facing resources
                ec2.SubnetConfiguration(
                    name='Public',
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                # Private — Lambda, RDS (no direct internet)
                ec2.SubnetConfiguration(
                    name='Private',
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # ── Security Group: Lambda ──────────────────────
        self.lambda_sg = ec2.SecurityGroup(
            self, 'LambdaSg',
            security_group_name=f'myapp-{environment}-lambda-sg',
            vpc=self.vpc,
            description='Security group for Lambda functions',
            allow_all_outbound=True,    # Lambda needs outbound for API calls
        )

        # ── Security Group: RDS ─────────────────────────
        self.rds_sg = ec2.SecurityGroup(
            self, 'RdsSg',
            security_group_name=f'myapp-{environment}-rds-sg',
            vpc=self.vpc,
            description='Security group for RDS database',
            allow_all_outbound=False,   # DB should not call outbound
        )

        # RDS only accepts connections FROM Lambda
        self.rds_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(5432),      # PostgreSQL port
            description='Allow PostgreSQL from Lambda only',
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'VpcId',
            value=self.vpc.vpc_id,
            description=f'VPC ID for {environment}',
            export_name=f'VpcId-{environment}',
        )

import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_events,
    aws_ec2 as ec2,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_events as events,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_ssm as ssm,
)
from constructs import Construct


class ComputeStack(cdk.Stack):
    """
    TICKET-08: Lambda Functions (Shell/Container)
    ──────────────────────────────────────────────
    DevOps creates the Lambda containers:
      - Runtime, memory, timeout configured
      - VPC placement (private subnet)
      - IAM permissions (least privilege)
      - Environment variables from SSM (not hardcoded)
      - Secrets from Secrets Manager

    Developer fills in the code inside services/ folder.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        vpc: ec2.Vpc,
        db_secret: secretsmanager.Secret,
        bucket: s3.Bucket,
        queue: sqs.Queue,
        event_bus: events.EventBus,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        is_prod = environment == 'prod'

        # ── Shared environment variables (read from SSM) ──
        shared_env = {
            'ENVIRONMENT':  environment,
            'LOG_LEVEL':    'ERROR' if is_prod else 'DEBUG',
            'AWS_ACCOUNT':  self.account,
            'AWS_REGION_NAME': self.region,

            # DB config (NOT password — that comes from Secrets Manager)
            'DB_PORT':      '5432',
            'DB_NAME':      'myappdb',
            'DB_HOST':      ssm.StringParameter.value_for_string_parameter(
                                self, f'/myapp/{environment}/database/host'
                            ),

            # S3
            'S3_BUCKET':    bucket.bucket_name,

            # Messaging
            'ORDERS_QUEUE_URL': queue.queue_url,
            'EVENT_BUS_NAME':   event_bus.event_bus_name,

            # Secret ARN (developer reads password at runtime)
            'DB_SECRET_ARN':    db_secret.secret_arn,
        }

        # ── Memory size per environment ──────────────────
        memory = 512 if is_prod else 256

        # ════════════════════════════════════════════════
        # LAMBDA: Users Handler
        # Developer writes: services/users/handler.py
        # ════════════════════════════════════════════════
        self.users_lambda = _lambda.Function(
            self, 'UsersLambda',
            function_name=f'myapp-{environment}-users',
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='handler.lambda_handler',        # ← developer must use this name
            code=_lambda.Code.from_asset('./services/users'),
            memory_size=memory,
            timeout=cdk.Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            environment=shared_env,
            log_retention=logs.RetentionDays.ONE_MONTH,
            tracing=_lambda.Tracing.ACTIVE,          # X-Ray tracing on
        )

        # ════════════════════════════════════════════════
        # LAMBDA: Orders Handler
        # Developer writes: services/orders/handler.py
        # ════════════════════════════════════════════════
        self.orders_lambda = _lambda.Function(
            self, 'OrdersLambda',
            function_name=f'myapp-{environment}-orders',
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='handler.lambda_handler',
            code=_lambda.Code.from_asset('./services/orders'),
            memory_size=memory,
            timeout=cdk.Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            environment=shared_env,
            log_retention=logs.RetentionDays.ONE_MONTH,
            tracing=_lambda.Tracing.ACTIVE,
        )

        # ════════════════════════════════════════════════
        # LAMBDA: Auth Handler
        # Developer writes: services/auth/handler.py
        # ════════════════════════════════════════════════
        self.auth_lambda = _lambda.Function(
            self, 'AuthLambda',
            function_name=f'myapp-{environment}-auth',
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='handler.lambda_handler',
            code=_lambda.Code.from_asset('./services/events'),
            memory_size=256,
            timeout=cdk.Duration.seconds(15),
            environment=shared_env,
            log_retention=logs.RetentionDays.ONE_MONTH,
        )

        # ════════════════════════════════════════════════
        # LAMBDA: Event Processor (triggered by SQS)
        # Developer writes: services/events/handler.py
        # ════════════════════════════════════════════════
        self.event_processor = _lambda.Function(
            self, 'EventProcessor',
            function_name=f'myapp-{environment}-event-processor',
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler='handler.lambda_handler',
            code=_lambda.Code.from_asset('./services/events'),
            memory_size=256,
            timeout=cdk.Duration.seconds(30),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            ),
            environment=shared_env,
            log_retention=logs.RetentionDays.ONE_MONTH,
        )

        # SQS → triggers event processor automatically
        self.event_processor.add_event_source(
            lambda_events.SqsEventSource(
                queue,
                batch_size=10,
                report_batch_item_failures=True,
            )
        )

        # ════════════════════════════════════════════════
        # IAM PERMISSIONS (least privilege)
        # ════════════════════════════════════════════════

        # Grant S3 access
        bucket.grant_read_write(self.users_lambda)
        bucket.grant_read_write(self.orders_lambda)

        # Grant SQS access
        queue.grant_send_messages(self.orders_lambda)
        queue.grant_consume_messages(self.event_processor)

        # Grant EventBridge publish
        event_bus.grant_put_events_to(self.orders_lambda)

        # Grant Secrets Manager read
        db_secret.grant_read(self.users_lambda)
        db_secret.grant_read(self.orders_lambda)
        db_secret.grant_read(self.event_processor)

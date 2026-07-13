import aws_cdk as cdk
from constructs import Construct

# Import all stacks
from stacks.vpc_stack import VpcStack
from stacks.security_stack import SecurityStack
from stacks.storage_stack import StorageStack
from stacks.database_stack import DatabaseStack
from stacks.auth_stack import AuthStack
from stacks.messaging_stack import MessagingStack
from stacks.compute_stack import ComputeStack
from stacks.api_stack import ApiStack
from stacks.monitoring_stack import MonitoringStack


class AppStage(cdk.Stage):
    """
    Groups ALL stacks for ONE environment (dev / staging / prod).
    The pipeline creates one AppStage per environment.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,       # 'dev' | 'staging' | 'prod'
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. Networking (must be first) ──────────────
        vpc_stack = VpcStack(
            self, 'VpcStack',
            environment=environment,
        )

        # ── 2. Security (Secrets + SSM) ─────────────────
        security_stack = SecurityStack(
            self, 'SecurityStack',
            environment=environment,
        )

        # ── 3. Storage (S3) ─────────────────────────────
        storage_stack = StorageStack(
            self, 'StorageStack',
            environment=environment,
        )

        # ── 4. Database (RDS) ───────────────────────────
        database_stack = DatabaseStack(
            self, 'DatabaseStack',
            environment=environment,
            vpc=vpc_stack.vpc,
        )
        database_stack.add_dependency(vpc_stack)
        database_stack.add_dependency(security_stack)

        # ── 5. Auth (Cognito) ───────────────────────────
        auth_stack = AuthStack(
            self, 'AuthStack',
            environment=environment,
        )

        # ── 6. Messaging (SQS + DLQ + EventBridge) ─────
        messaging_stack = MessagingStack(
            self, 'MessagingStack',
            environment=environment,
        )

        # ── 7. Compute (Lambda functions) ───────────────
        compute_stack = ComputeStack(
            self, 'ComputeStack',
            environment=environment,
            vpc=vpc_stack.vpc,
            db_secret=security_stack.db_secret,
            bucket=storage_stack.app_bucket,
            queue=messaging_stack.orders_queue,
            event_bus=messaging_stack.event_bus,
        )
        compute_stack.add_dependency(database_stack)
        compute_stack.add_dependency(messaging_stack)

        # ── 8. API Gateway ──────────────────────────────
        api_stack = ApiStack(
            self, 'ApiStack',
            environment=environment,
            user_pool=auth_stack.user_pool,
            users_lambda=compute_stack.users_lambda,
            orders_lambda=compute_stack.orders_lambda,
            auth_lambda=compute_stack.auth_lambda,
        )
        api_stack.add_dependency(compute_stack)
        api_stack.add_dependency(auth_stack)

        # ── 9. Monitoring (CloudWatch) ──────────────────
        monitoring_stack = MonitoringStack(
            self, 'MonitoringStack',
            environment=environment,
            users_lambda=compute_stack.users_lambda,
            orders_lambda=compute_stack.orders_lambda,
            orders_queue=messaging_stack.orders_queue,
            orders_dlq=messaging_stack.orders_dlq,
            api=api_stack.api,
        )
        monitoring_stack.add_dependency(api_stack)

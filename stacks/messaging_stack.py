import aws_cdk as cdk
from aws_cdk import (
    aws_sqs as sqs,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct


class MessagingStack(cdk.Stack):
    """
    TICKET-07: SQS + DLQ + EventBridge
    ────────────────────────────────────
    SQS Queues    → Reliable async message processing
    DLQ           → Catch failed messages (never lose data)
    EventBridge   → Route events between services
    SNS           → Alert team on critical events
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ════════════════════════════════════════════════
        # DEAD LETTER QUEUES (catch failures)
        # ════════════════════════════════════════════════

        # DLQ for orders
        self.orders_dlq = sqs.Queue(
            self, 'OrdersDlq',
            queue_name=f'myapp-{environment}-orders-dlq',
            retention_period=cdk.Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )

        # DLQ for notifications
        self.notifications_dlq = sqs.Queue(
            self, 'NotificationsDlq',
            queue_name=f'myapp-{environment}-notifications-dlq',
            retention_period=cdk.Duration.days(14),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
        )

        # ════════════════════════════════════════════════
        # SQS QUEUES (main queues)
        # ════════════════════════════════════════════════

        # Orders processing queue
        self.orders_queue = sqs.Queue(
            self, 'OrdersQueue',
            queue_name=f'myapp-{environment}-orders-queue',
            visibility_timeout=cdk.Duration.seconds(30),
            retention_period=cdk.Duration.days(4),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,         # try 3 times → then DLQ
                queue=self.orders_dlq,
            ),
        )

        # Notifications queue
        self.notifications_queue = sqs.Queue(
            self, 'NotificationsQueue',
            queue_name=f'myapp-{environment}-notifications-queue',
            visibility_timeout=cdk.Duration.seconds(30),
            retention_period=cdk.Duration.days(4),
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.notifications_dlq,
            ),
        )

        # ════════════════════════════════════════════════
        # EVENTBRIDGE — Central Event Bus
        # ════════════════════════════════════════════════

        self.event_bus = events.EventBus(
            self, 'AppEventBus',
            event_bus_name=f'myapp-{environment}-events',
        )

        # Rule 1: OrderPlaced → orders queue
        events.Rule(
            self, 'OrderPlacedRule',
            event_bus=self.event_bus,
            rule_name=f'myapp-{environment}-order-placed',
            description='Route OrderPlaced events to orders queue',
            event_pattern=events.EventPattern(
                source=['myapp.orders'],
                detail_type=['OrderPlaced'],
            ),
            targets=[targets.SqsQueue(self.orders_queue)],
        )

        # Rule 2: Any event → notifications queue
        events.Rule(
            self, 'NotificationRule',
            event_bus=self.event_bus,
            rule_name=f'myapp-{environment}-notifications',
            description='Route notification events to notifications queue',
            event_pattern=events.EventPattern(
                source=['myapp.users', 'myapp.orders'],
                detail_type=['UserSignedUp', 'OrderShipped'],
            ),
            targets=[targets.SqsQueue(self.notifications_queue)],
        )

        # ════════════════════════════════════════════════
        # SNS — Alerts 
        # ════════════════════════════════════════════════

        self.alerts_topic = sns.Topic(
            self, 'AlertsTopic',
            topic_name=f'myapp-{environment}-alerts',
            display_name=f'MyApp {environment.upper()} Alerts',
        )

        
        self.alerts_topic.add_subscription(
            subs.EmailSubscription('khuzaimah.arshad@powersoft19.com')
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'OrdersQueueUrl',
            value=self.orders_queue.queue_url,
            export_name=f'OrdersQueueUrl-{environment}',
        )

        cdk.CfnOutput(self, 'EventBusName',
            value=self.event_bus.event_bus_name,
            export_name=f'EventBusName-{environment}',
        )

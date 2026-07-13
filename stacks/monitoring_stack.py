import aws_cdk as cdk
from aws_cdk import (
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cw_actions,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_apigateway as apigw,
    aws_sns as sns,
    aws_logs as logs,
)
from constructs import Construct


class MonitoringStack(cdk.Stack):
    """
    TICKET-10: CloudWatch Monitoring
    ──────────────────────────────────
    Alarms     → Alert when something goes wrong
    Dashboard  → Visual overview of all services
    Log Groups → Centralized logging with retention
    SNS Alerts → Email DevOps team on critical issues
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        users_lambda: _lambda.Function,
        orders_lambda: _lambda.Function,
        orders_queue: sqs.Queue,
        orders_dlq: sqs.Queue,
        api: apigw.RestApi,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        is_prod = environment == 'prod'

        # ── SNS Alert Topic ──────────────────────────────
        alert_topic = sns.Topic(
            self, 'AlertTopic',
            topic_name=f'myapp-{environment}-monitoring-alerts',
        )

        def alarm_action():
            return cw_actions.SnsAction(alert_topic)

        # ════════════════════════════════════════════════
        # LAMBDA ALARMS
        # ════════════════════════════════════════════════

        for fn, name in [
            (users_lambda, 'Users'),
            (orders_lambda, 'Orders'),
        ]:
            # Error rate alarm
            error_alarm = cloudwatch.Alarm(
                self, f'{name}ErrorAlarm',
                alarm_name=f'myapp-{environment}-{name.lower()}-errors',
                alarm_description=f'{name} Lambda error rate too high',
                metric=fn.metric_errors(
                    period=cdk.Duration.minutes(1),
                    statistic='Sum',
                ),
                threshold=5,
                evaluation_periods=1,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )
            error_alarm.add_alarm_action(alarm_action())

            # Duration alarm (near timeout of 30s)
            cloudwatch.Alarm(
                self, f'{name}DurationAlarm',
                alarm_name=f'myapp-{environment}-{name.lower()}-duration',
                alarm_description=f'{name} Lambda running too slow',
                metric=fn.metric_duration(
                    period=cdk.Duration.minutes(5),
                    statistic='p99',
                ),
                threshold=25000,    # 25 seconds (timeout is 30s)
                evaluation_periods=3,
                comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
                treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            )

        # ════════════════════════════════════════════════
        # SQS / DLQ ALARMS
        # ════════════════════════════════════════════════

        # DLQ alarm — CRITICAL (message failed 3 times!)
        dlq_alarm = cloudwatch.Alarm(
            self, 'OrdersDlqAlarm',
            alarm_name=f'myapp-{environment}-orders-dlq-messages',
            alarm_description='Messages in DLQ — investigate immediately!',
            metric=orders_dlq.metric_approximate_number_of_messages_visible(
                period=cdk.Duration.minutes(1),
                statistic='Sum',
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        dlq_alarm.add_alarm_action(alarm_action())

        # ════════════════════════════════════════════════
        # API GATEWAY ALARMS
        # ════════════════════════════════════════════════

        # 5XX errors alarm
        cloudwatch.Alarm(
            self, 'Api5xxAlarm',
            alarm_name=f'myapp-{environment}-api-5xx-errors',
            alarm_description='API 5XX errors too high',
            metric=api.metric_server_error(
                period=cdk.Duration.minutes(5),
                statistic='Sum',
            ),
            threshold=10,
            evaluation_periods=2,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        # ════════════════════════════════════════════════
        # CLOUDWATCH DASHBOARD
        # ════════════════════════════════════════════════

        dashboard = cloudwatch.Dashboard(
            self, 'AppDashboard',
            dashboard_name=f'myapp-{environment}-dashboard',
        )

        dashboard.add_widgets(
            # Row 1: API Gateway
            cloudwatch.GraphWidget(
                title='API Gateway — Requests & Errors',
                left=[
                    api.metric_count(),
                    api.metric_server_error(),
                    api.metric_client_error(),
                ],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title='API Gateway — Latency',
                left=[api.metric_latency(statistic='p99')],
                width=12,
            ),
        )

        dashboard.add_widgets(
            # Row 2: Lambda
            cloudwatch.GraphWidget(
                title='Lambda — Invocations & Errors',
                left=[
                    users_lambda.metric_invocations(),
                    users_lambda.metric_errors(),
                    orders_lambda.metric_invocations(),
                    orders_lambda.metric_errors(),
                ],
                width=12,
            ),
            cloudwatch.GraphWidget(
                title='SQS — Queue Depth & DLQ',
                left=[
                    orders_queue.metric_approximate_number_of_messages_visible(),
                    orders_dlq.metric_approximate_number_of_messages_visible(),
                ],
                width=12,
            ),
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'DashboardUrl',
            value=f'https://{self.region}.console.aws.amazon.com/cloudwatch/home#dashboards:name=myapp-{environment}-dashboard',
            description='CloudWatch Dashboard URL',
        )

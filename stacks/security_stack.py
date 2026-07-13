import aws_cdk as cdk
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
    aws_ssm as ssm,
)
from constructs import Construct


class SecurityStack(cdk.Stack):
    """
    TICKET-03: Secrets Manager & SSM Parameter Store
    ─────────────────────────────────────────────────
    Secrets Manager  → Sensitive data (passwords, keys)
    SSM Param Store  → Config data (hostnames, settings)

    Developers read these via env vars YOU set in compute_stack.py
    They NEVER hardcode passwords!
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
        # SECRETS MANAGER — Sensitive Values
        # ════════════════════════════════════════════════

        # Database credentials (auto-generated password)
        self.db_secret = secretsmanager.Secret(
            self, 'DbSecret',
            secret_name=f'/myapp/{environment}/database/credentials',
            description=f'RDS PostgreSQL credentials for {environment}',
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"username": "dbadmin"}',
                generate_string_key='password',
                exclude_characters='/@" \'\\',
                password_length=32,
            ),
        )

        # API Secret Key (for JWT signing etc.)
        self.api_secret = secretsmanager.Secret(
            self, 'ApiSecret',
            secret_name=f'/myapp/{environment}/api/secret-key',
            description=f'API secret key for {environment}',
            generate_secret_string=secretsmanager.SecretStringGenerator(
                password_length=64,
                exclude_punctuation=False,
            ),
        )

        # ════════════════════════════════════════════════
        # SSM PARAMETER STORE — Non-sensitive Config
        # ════════════════════════════════════════════════

        # Log level per environment
        ssm.StringParameter(
            self, 'LogLevel',
            parameter_name=f'/myapp/{environment}/app/log-level',
            string_value='DEBUG' if environment == 'dev' else 'INFO',
            description='Application log level',
        )

        # Environment name
        ssm.StringParameter(
            self, 'EnvName',
            parameter_name=f'/myapp/{environment}/app/environment',
            string_value=environment,
            description='Current environment name',
        )

        # AWS Region
        ssm.StringParameter(
            self, 'AwsRegion',
            parameter_name=f'/myapp/{environment}/app/region',
            string_value=self.region,
            description='AWS Region',
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'DbSecretArn',
            value=self.db_secret.secret_arn,
            description='DB Secret ARN',
            export_name=f'DbSecretArn-{environment}',
        )

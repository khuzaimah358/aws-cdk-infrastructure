import aws_cdk as cdk
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class AuthStack(cdk.Stack):
    """
    TICKET-06: Cognito Authentication
    ───────────────────────────────────
    User Pool     → Stores users, handles sign-up/login
    App Client    → Frontend connects via this
    API Authorizer is attached in api_stack.py
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── User Pool ───────────────────────────────────
        self.user_pool = cognito.UserPool(
            self, 'UserPool',
            user_pool_name=f'myapp-{environment}-user-pool',

            # Sign-in options
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False,
            ),

            # Auto-verify email
            auto_verify=cognito.AutoVerifiedAttrs(email=True),

            # Required user attributes
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True,
                ),
                fullname=cognito.StandardAttribute(
                    required=False,
                    mutable=True,
                ),
            ),

            # Password policy
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),

            # Account recovery via email
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,

            # Cleanup
            removal_policy=(
                cdk.RemovalPolicy.RETAIN
                if environment == 'prod'
                else cdk.RemovalPolicy.DESTROY
            ),
        )

        # ── App Client (used by frontend) ───────────────
        self.user_pool_client = self.user_pool.add_client(
            'AppClient',
            user_pool_client_name=f'myapp-{environment}-client',

            # Token validity
            access_token_validity=cdk.Duration.hours(1),
            id_token_validity=cdk.Duration.hours(1),
            refresh_token_validity=cdk.Duration.days(30),

            # Auth flows
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),

            # No secret for public clients (SPAs, mobile)
            generate_secret=False,
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'UserPoolId',
            value=self.user_pool.user_pool_id,
            description=f'Cognito User Pool ID for {environment}',
            export_name=f'UserPoolId-{environment}',
        )

        cdk.CfnOutput(self, 'UserPoolClientId',
            value=self.user_pool_client.user_pool_client_id,
            description='User Pool Client ID',
            export_name=f'UserPoolClientId-{environment}',
        )

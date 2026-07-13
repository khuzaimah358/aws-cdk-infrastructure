import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_lambda as _lambda,
)
from constructs import Construct


class ApiStack(cdk.Stack):
    """
    TICKET-09: API Gateway
    ───────────────────────
    REST API with:
      - Public routes  (/auth/*)   — no token needed
      - Protected routes (/users, /orders) — JWT token required
      - Cognito Authorizer validates tokens
      - CORS enabled for frontend access
      - Throttling to prevent abuse
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        user_pool: cognito.UserPool,
        users_lambda: _lambda.Function,
        orders_lambda: _lambda.Function,
        auth_lambda: _lambda.Function,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── REST API ────────────────────────────────────
        self.api = apigw.RestApi(
            self, 'MyApi',
            rest_api_name=f'myapp-{environment}-api',
            description=f'MyApp REST API - {environment}',
            deploy_options=apigw.StageOptions(
                stage_name=environment,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=(environment != 'prod'),
                throttling_rate_limit=1000,
                throttling_burst_limit=500,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=[
                    'Content-Type',
                    'Authorization',
                    'X-Api-Key',
                ],
            ),
        )

        # ── Cognito Authorizer ──────────────────────────
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self, 'CognitoAuthorizer',
            cognito_user_pools=[user_pool],
            authorizer_name=f'myapp-{environment}-authorizer',
            identity_source='method.request.header.Authorization',
        )

        # ── Lambda Integrations ─────────────────────────
        users_integration  = apigw.LambdaIntegration(users_lambda)
        orders_integration = apigw.LambdaIntegration(orders_lambda)
        auth_integration   = apigw.LambdaIntegration(auth_lambda)

        # ════════════════════════════════════════════════
        # PUBLIC ROUTES — /auth/* (no token required)
        # ════════════════════════════════════════════════
        auth_resource = self.api.root.add_resource('auth')

        auth_resource.add_resource('register').add_method(
            'POST', auth_integration,
        )
        auth_resource.add_resource('login').add_method(
            'POST', auth_integration,
        )

        # ════════════════════════════════════════════════
        # PROTECTED ROUTES — /users (JWT token required)
        # ════════════════════════════════════════════════
        users_resource = self.api.root.add_resource('users')

        # GET  /users       → list all users
        # POST /users       → create user
        users_resource.add_method(
            'GET', users_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )
        users_resource.add_method(
            'POST', users_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        # /users/{id}
        user_by_id = users_resource.add_resource('{id}')
        for method in ['GET', 'PUT', 'DELETE']:
            user_by_id.add_method(
                method, users_integration,
                authorization_type=apigw.AuthorizationType.COGNITO,
                authorizer=authorizer,
            )

        # ════════════════════════════════════════════════
        # PROTECTED ROUTES — /orders
        # ════════════════════════════════════════════════
        orders_resource = self.api.root.add_resource('orders')

        orders_resource.add_method(
            'GET', orders_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )
        orders_resource.add_method(
            'POST', orders_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        order_by_id = orders_resource.add_resource('{id}')
        order_by_id.add_method(
            'GET', orders_integration,
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        # ── Health Check (public) ───────────────────────
        self.api.root.add_resource('health').add_method(
            'GET', apigw.MockIntegration(
                integration_responses=[apigw.IntegrationResponse(
                    status_code='200',
                    response_templates={'application/json': '{"status": "ok"}'},
                )],
                passthrough_behavior=apigw.PassthroughBehavior.NEVER,
                request_templates={'application/json': '{"statusCode": 200}'},
            ),
            method_responses=[apigw.MethodResponse(status_code='200')],
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'ApiUrl',
            value=self.api.url,
            description=f'API Gateway URL for {environment}',
            export_name=f'ApiUrl-{environment}',
        )

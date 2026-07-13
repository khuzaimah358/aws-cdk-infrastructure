import aws_cdk as cdk
from aws_cdk import aws_s3 as s3
from constructs import Construct


class StorageStack(cdk.Stack):
    """
    TICKET-04: S3 Buckets
    ──────────────────────
    app_bucket    → App assets, user uploads
    logs_bucket   → Archived application logs
    artifacts_bucket → CI/CD build outputs
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        removal = (
            cdk.RemovalPolicy.DESTROY
            if environment == 'dev'
            else cdk.RemovalPolicy.RETAIN    # Keep data in staging/prod!
        )

        # ── App Bucket (main) ───────────────────────────
        self.app_bucket = s3.Bucket(
            self, 'AppBucket',
            bucket_name=f'myapp-{environment}-app-{self.account}',
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=(environment == 'dev'),
            lifecycle_rules=[
                s3.LifecycleRule(
                    id='MoveToGlacier',
                    enabled=True,
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=cdk.Duration.days(90),
                        )
                    ],
                )
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.POST,
                    ],
                    allowed_origins=['*'],    # restrict in prod!
                    allowed_headers=['*'],
                )
            ],
        )

        # ── Logs Bucket ─────────────────────────────────
        self.logs_bucket = s3.Bucket(
            self, 'LogsBucket',
            bucket_name=f'myapp-{environment}-logs-{self.account}',
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=(environment == 'dev'),
        )

        # ── Artifacts Bucket ────────────────────────────
        self.artifacts_bucket = s3.Bucket(
            self, 'ArtifactsBucket',
            bucket_name=f'myapp-{environment}-artifacts-{self.account}',
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=removal,
            auto_delete_objects=(environment == 'dev'),
        )

        # ── Outputs ─────────────────────────────────────
        cdk.CfnOutput(self, 'AppBucketName',
            value=self.app_bucket.bucket_name,
            export_name=f'AppBucketName-{environment}',
        )

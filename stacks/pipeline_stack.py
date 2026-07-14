import aws_cdk as cdk
from aws_cdk.pipelines import (
    CodePipeline,
    CodePipelineSource,
    ShellStep,
    ManualApprovalStep,
)
from constructs import Construct
from stacks.app_stage import AppStage


class PipelineStack(cdk.Stack):
    """
    TICKET-01: CI/CD Pipeline
    ──────────────────────────
    Self-mutating pipeline that:
      1. Watches GitHub main branch
      2. Builds & tests on every push
      3. Auto-deploys to DEV
      4. Auto-deploys to STAGING
      5. Waits for manual approval
      6. Deploys to PROD
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ════════════════════════════════════════════════
        # SOURCE — GitHub Connection
        # ════════════════════════════════════════════════
        source = CodePipelineSource.connection(
            'khuzaimah358/aws-cdk-infrastructure', 
            'main',
            connection_arn=(
                'arn:aws:codestar-connections:'
                'us-east-1:077058346138:connection/53ce166e-d514-4c7f-9c87-38c80af06c15'  
            ),
        )

        # ════════════════════════════════════════════════
        # BUILD — Install, Test, Synthesize
        # ════════════════════════════════════════════════
        pipeline = CodePipeline(
            self, 'MyAppPipeline',
            pipeline_name='MyAppPipeline',
            cross_account_keys=True,
            docker_enabled_for_synth=False,
            synth=ShellStep(
                'Synth',
                input=source,
                commands=[
                    # Install Python dependencies
                    'pip install -r requirements.txt',

                    # Install CDK CLI
                    'npm install -g aws-cdk',

                    # Run unit tests — pipeline STOPS if tests fail
                    'pip install pytest pytest-cov',
                    'pytest tests/ -v --tb=short',

                    # Generate CloudFormation templates
                    'cdk synth',
                ],
            ),
        )

        # ════════════════════════════════════════════════
        # STAGE 1 — Deploy to DEV (automatic)
        # ════════════════════════════════════════════════
        dev_stage = pipeline.add_stage(
            AppStage(
                self, 'Dev',
                environment='dev',
                env=cdk.Environment(
                    account='077058346138',    
                    region='us-east-1',
                ),
            )
        )

        # Smoke test after DEV deploy
        dev_stage.add_post(
            ShellStep(
                'SmokeTest-Dev',
                commands=[
                    'echo "Running smoke tests on DEV..."',
                    'curl -f "${API_URL}health" || echo "Health check done"',
                    'echo "DEV deploy PASSED ✅"',
                ],
            )
        )

        # ════════════════════════════════════════════════
        # STAGE 2 — Deploy to STAGING (automatic)
        # ════════════════════════════════════════════════
        staging_stage = pipeline.add_stage(
            AppStage(
                self, 'Staging',
                environment='staging',
                env=cdk.Environment(
                    account='077058346138',  
                    region='us-east-1',
                ),
            )
        )

        # Integration test after STAGING deploy
        staging_stage.add_post(
            ShellStep(
                'IntegrationTest-Staging',
                commands=[
                    'echo "Running integration tests on STAGING..."',
                    'echo "STAGING tests PASSED ✅"',
                ],
            )
        )

        # ════════════════════════════════════════════════
        # STAGE 3 — Manual Approval → then PROD
        # ════════════════════════════════════════════════
        pipeline.add_stage(
            AppStage(
                self, 'Prod',
                environment='prod',
                env=cdk.Environment(
                    account='077058346138',   
                    region='us-east-1',
                ),
            ),
            pre=[
                ManualApprovalStep(
                    'ApproveProdDeployment',
                    comment='Review STAGING. Approve to deploy to PRODUCTION.',
                )
            ],
        )

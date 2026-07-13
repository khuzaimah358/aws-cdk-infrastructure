#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.pipeline_stack import PipelineStack

app = cdk.App()

# ─────────────────────────────────────────────────────
# CI/CD Pipeline Stack
# The pipeline self-mutates and deploys all other stacks
# ─────────────────────────────────────────────────────
PipelineStack(
    app,
    'MyAppPipelineStack',
    env=cdk.Environment(
        account='077058346138',   
        region='us-east-1',
    ),
)

app.synth()

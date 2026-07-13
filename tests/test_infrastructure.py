import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Template, Match
from stacks.vpc_stack import VpcStack
from stacks.storage_stack import StorageStack
from stacks.compute_stack import ComputeStack


@pytest.fixture
def vpc_template():
    app = cdk.App()
    stack = VpcStack(app, 'TestVpcStack', environment='dev')
    return Template.from_stack(stack)


@pytest.fixture
def storage_template():
    app = cdk.App()
    stack = StorageStack(app, 'TestStorageStack', environment='dev')
    return Template.from_stack(stack)


# ── VPC Tests ──────────────────────────────────────────────
def test_vpc_created(vpc_template):
    vpc_template.resource_count_is('AWS::EC2::VPC', 1)


def test_vpc_has_correct_cidr(vpc_template):
    vpc_template.has_resource_properties('AWS::EC2::VPC', {
        'CidrBlock': '10.0.0.0/16',
    })


def test_subnets_created(vpc_template):
    # Should have 4 subnets: 2 public + 2 private (2 AZs)
    vpc_template.resource_count_is('AWS::EC2::Subnet', 4)


def test_nat_gateway_created(vpc_template):
    vpc_template.resource_count_is('AWS::EC2::NatGateway', 1)


def test_security_groups_created(vpc_template):
    # Lambda SG + RDS SG
    vpc_template.resource_count_is('AWS::EC2::SecurityGroup', 2)


# ── Storage Tests ───────────────────────────────────────────
def test_buckets_created(storage_template):
    storage_template.resource_count_is('AWS::S3::Bucket', 3)


def test_app_bucket_versioned(storage_template):
    storage_template.has_resource_properties('AWS::S3::Bucket', {
        'VersioningConfiguration': {'Status': 'Enabled'},
    })


def test_public_access_blocked(storage_template):
    storage_template.has_resource_properties('AWS::S3::Bucket', {
        'PublicAccessBlockConfiguration': {
            'BlockPublicAcls': True,
            'BlockPublicPolicy': True,
            'IgnorePublicAcls': True,
            'RestrictPublicBuckets': True,
        },
    })

import boto3
import pytest
from moto import mock_aws
import os
import json
from prog_assignment_1.assignment import (
    create_roles_and_policies,
    create_iam_user,
    add_user_permissions,
    assume_role,
    create_s3_resources,
    list_and_compute_size,
    cleanup_s3_resources,
    cleanup_iam_resources,
    BUCKET_NAME,
    DEV_ROLE_NAME,
    USER_ROLE_NAME,
    IAM_USER_NAME,
)

# --- Fixtures for setting up mock AWS environment ---

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"

@pytest.fixture(scope="function")
def iam_client(aws_credentials):
    with mock_aws():
        yield boto3.client("iam", region_name="us-east-1")

@pytest.fixture(scope="function")
def s3_client(aws_credentials):
    with mock_aws():
        yield boto3.client("s3", region_name="us-east-1")

@pytest.fixture(scope="function")
def sts_client(aws_credentials):
    with mock_aws():
        yield boto3.client("sts", region_name="us-east-1")

@pytest.fixture(scope="function")
def dummy_files():
    """Create dummy files for testing uploads."""
    files = ["assignment1.txt", "assignment2.txt", "recording1.jpg"]
    content = {
        "assignment1.txt": "Empty Assignment 1",
        "assignment2.txt": "Empty Assignment 2",
        "recording1.jpg": "dummy_image_data",
    }
    for f in files:
        with open(f, "w") as file:
            file.write(content[f])
    yield
    for f in files:
        os.remove(f)

@pytest.fixture(scope="function")
def setup_iam_and_s3(iam_client, sts_client, s3_client, dummy_files):
    """A comprehensive fixture to set up the entire environment for tests."""
    account_id = sts_client.get_caller_identity()["Account"]
    region = s3_client.meta.region_name

    # Create a mock policy for the Dev role to simulate AmazonS3FullAccess
    dev_policy_document = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}
    dev_policy = iam_client.create_policy(PolicyName="S3FullAccess", PolicyDocument=json.dumps(dev_policy_document))
    dev_policy_arn = dev_policy["Policy"]["Arn"]

    # --- Create all resources ---
    create_roles_and_policies(iam_client, account_id, dev_policy_arn)
    create_iam_user(iam_client)
    add_user_permissions(iam_client, account_id)

    # --- Yield clients and identifiers ---
    yield {
        "iam_client": iam_client,
        "sts_client": sts_client,
        "s3_client": s3_client,
        "account_id": account_id,
        "region": region,
        "dev_policy_arn": dev_policy_arn
    }

    # --- Teardown ---
    # The cleanup functions from the main script are tested in test_cleanup
    try:
        cleanup_iam_resources(iam_client, dev_policy_arn)
        iam_client.delete_policy(PolicyArn=dev_policy_arn)
    except Exception as e:
        print(f"Error during IAM cleanup in fixture: {e}")


# --- Granular Tests for Each Requirement ---

def test_role_and_policy_creation(setup_iam_and_s3):
    """Req 1 & 2: Verify IAM roles and policies are created correctly."""
    iam_client = setup_iam_and_s3["iam_client"]

    # Verify Dev role and its S3 full access policy
    dev_attached_policies = iam_client.list_attached_role_policies(RoleName=DEV_ROLE_NAME)
    assert dev_attached_policies["AttachedPolicies"][0]["PolicyName"] == "S3FullAccess"

    # Verify User role and its inline list/get policy
    user_inline_policy = iam_client.get_role_policy(RoleName=USER_ROLE_NAME, PolicyName="S3ListAndGet")
    policy_statement = user_inline_policy["PolicyDocument"]["Statement"][0]
    expected_actions = ["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetObject"]
    assert all(action in policy_statement["Action"] for action in expected_actions)
    assert policy_statement["Effect"] == "Allow"

def test_user_creation(setup_iam_and_s3):
    """Req 3: Verify the IAM user is created and has assume-role permissions."""
    iam_client = setup_iam_and_s3["iam_client"]
    user_policies = iam_client.list_user_policies(UserName=IAM_USER_NAME)["PolicyNames"]
    assert "AllowAssumeDevUserRoles" in user_policies

def test_dev_role_s3_actions(setup_iam_and_s3):
    """Req 4: Verify the Dev role can create buckets and objects."""
    sts_client = setup_iam_and_s3["sts_client"]
    account_id = setup_iam_and_s3["account_id"]
    region = setup_iam_and_s3["region"]

    # Assume Dev role
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{DEV_ROLE_NAME}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=dev_credentials["AccessKeyId"],
        aws_secret_access_key=dev_credentials["SecretAccessKey"],
        aws_session_token=dev_credentials["SessionToken"],
    )

    # Create S3 resources
    create_s3_resources(s3_dev_client)

    # Verify bucket and objects exist
    assert s3_dev_client.list_buckets()["Buckets"][0]["Name"] == BUCKET_NAME
    objects = s3_dev_client.list_objects_v2(Bucket=BUCKET_NAME)["Contents"]
    object_keys = [obj["Key"] for obj in objects]
    assert len(objects) == 3
    assert "assignment1.txt" in object_keys
    assert "assignment2.txt" in object_keys
    assert "recording1.jpg" in object_keys

def test_user_role_s3_actions(setup_iam_and_s3):
    """Req 5: Verify the User role can find objects and compute their size."""
    sts_client = setup_iam_and_s3["sts_client"]
    account_id = setup_iam_and_s3["account_id"]
    region = setup_iam_and_s3["region"]

    # First, use Dev role to create resources for the test
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{DEV_ROLE_NAME}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client("s3", region_name=region, aws_access_key_id=dev_credentials["AccessKeyId"], aws_secret_access_key=dev_credentials["SecretAccessKey"], aws_session_token=dev_credentials["SessionToken"])
    create_s3_resources(s3_dev_client)

    # Now, assume User role to test its permissions
    user_role_arn = f"arn:aws:iam::{account_id}:role/{USER_ROLE_NAME}"
    user_credentials = assume_role(sts_client, user_role_arn, "UserSession")
    s3_user_client = boto3.client("s3", region_name=region, aws_access_key_id=user_credentials["AccessKeyId"], aws_secret_access_key=user_credentials["SecretAccessKey"], aws_session_token=user_credentials["SessionToken"])

    # Find objects and compute size
    total_size = list_and_compute_size(s3_user_client)
    expected_size = os.path.getsize("assignment1.txt") + os.path.getsize("assignment2.txt")
    assert total_size == expected_size

def test_resource_cleanup(setup_iam_and_s3):
    """Req 6: Verify the Dev role can delete S3 resources and that IAM cleanup works."""
    iam_client = setup_iam_and_s3["iam_client"]
    sts_client = setup_iam_and_s3["sts_client"]
    s3_client = setup_iam_and_s3["s3_client"]
    account_id = setup_iam_and_s3["account_id"]
    region = setup_iam_and_s3["region"]
    dev_policy_arn = setup_iam_and_s3["dev_policy_arn"]

    # Assume Dev role to create and then clean up S3 resources
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{DEV_ROLE_NAME}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client("s3", region_name=region, aws_access_key_id=dev_credentials["AccessKeyId"], aws_secret_access_key=dev_credentials["SecretAccessKey"], aws_session_token=dev_credentials["SessionToken"])

    create_s3_resources(s3_dev_client)
    cleanup_s3_resources(s3_dev_client)

    # Verify S3 bucket is gone
    with pytest.raises(s3_client.exceptions.ClientError) as e:
        s3_client.head_bucket(Bucket=BUCKET_NAME)
    assert "404" in str(e.value)

    # Verify IAM cleanup
    cleanup_iam_resources(iam_client, dev_policy_arn)
    iam_client.delete_policy(PolicyArn=dev_policy_arn) # Clean up the test-specific policy

    assert len(iam_client.list_roles()["Roles"]) == 0
    assert len(iam_client.list_users()["Users"]) == 0
    assert len(iam_client.list_policies(Scope="Local")["Policies"]) == 0
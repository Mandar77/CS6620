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
    IAM_USER_NAME
)

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
    with open("assignment1.txt", "w") as f: f.write("Empty Assignment 1")
    with open("assignment2.txt", "w") as f: f.write("Empty Assignment 2")
    with open("recording1.jpg", "w") as f: f.write("dummy_image_data")
    yield
    os.remove("assignment1.txt")
    os.remove("assignment2.txt")
    os.remove("recording1.jpg")

@mock_aws
def test_full_workflow(iam_client, sts_client, s3_client, dummy_files):
    """Test the entire workflow from creation to cleanup."""
    account_id = sts_client.get_caller_identity()["Account"]
    region = s3_client.meta.region_name

    # --- Setup: Create mock policies and user ---
    dev_policy_document = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]}
    dev_policy = iam_client.create_policy(PolicyName="S3FullAccess", PolicyDocument=json.dumps(dev_policy_document))
    dev_policy_arn = dev_policy["Policy"]["Arn"]

    # --- Test Execution ---
    # 1. Create roles and policies
    create_roles_and_policies(iam_client, account_id, dev_policy_arn)
    assert len(iam_client.list_roles()["Roles"]) == 2

    # 2. Create IAM user and add permissions
    create_iam_user(iam_client)
    add_user_permissions(iam_client, account_id)
    assert len(iam_client.list_users()["Users"]) == 1
    assert iam_client.list_user_policies(UserName=IAM_USER_NAME)["PolicyNames"] == ["AllowAssumeDevUserRoles"]

    # 3. Assume Dev role and create S3 resources
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{DEV_ROLE_NAME}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=dev_credentials["AccessKeyId"],
        aws_secret_access_key=dev_credentials["SecretAccessKey"],
        aws_session_token=dev_credentials["SessionToken"],
    )
    create_s3_resources(s3_dev_client)
    assert s3_dev_client.list_buckets()["Buckets"][0]["Name"] == BUCKET_NAME
    assert len(s3_dev_client.list_objects_v2(Bucket=BUCKET_NAME)["Contents"]) == 3

    # 4. Assume User role, list objects, and compute size
    user_role_arn = f"arn:aws:iam::{account_id}:role/{USER_ROLE_NAME}"
    user_credentials = assume_role(sts_client, user_role_arn, "UserSession")
    s3_user_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=user_credentials["AccessKeyId"],
        aws_secret_access_key=user_credentials["SecretAccessKey"],
        aws_session_token=user_credentials["SessionToken"],
    )
    total_size = list_and_compute_size(s3_user_client)
    expected_size = os.path.getsize("assignment1.txt") + os.path.getsize("assignment2.txt")
    assert total_size == expected_size

    # 5. Clean up S3 resources
    cleanup_s3_resources(s3_dev_client)
    with pytest.raises(s3_client.exceptions.ClientError):
        s3_client.head_bucket(Bucket=BUCKET_NAME)

    # 6. Clean up IAM resources
    cleanup_iam_resources(iam_client, dev_policy_arn)
    iam_client.delete_policy(PolicyArn=dev_policy_arn) # Test-specific cleanup
    assert len(iam_client.list_roles()["Roles"]) == 0
    assert len(iam_client.list_users()["Users"]) == 0
    assert len(iam_client.list_policies(Scope="Local")["Policies"]) == 0
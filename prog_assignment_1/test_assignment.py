import boto3
import pytest
from moto import mock_aws
import os
import json
from prog_assignment_1.assignment import (
    create_roles_and_policies,
    create_iam_user,
    assume_role,
    create_s3_resources,
    list_and_compute_size,
    cleanup_s3_resources,
    bucket_name,
    dev_role_name,
    user_role_name,
    iam_user_name
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
    with open("assignment1.txt", "w") as f:
        f.write("Empty Assignment 1")
    with open("assignment2.txt", "w") as f:
        f.write("Empty Assignment 2")
    with open("recording1.jpg", "w") as f:
        f.write("dummy_image_data")
    yield
    os.remove("assignment1.txt")
    os.remove("assignment2.txt")
    os.remove("recording1.jpg")

@mock_aws
def test_full_workflow(iam_client, sts_client, s3_client, dummy_files):
    """Test the entire workflow from creation to cleanup."""
    account_id = sts_client.get_caller_identity()["Account"]

    # Create a mock policy for the Dev role
    dev_policy_document = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}],
    }
    dev_policy = iam_client.create_policy(
        PolicyName="S3FullAccess", PolicyDocument=json.dumps(dev_policy_document)
    )
    dev_policy_arn = dev_policy["Policy"]["Arn"]

    # 1. Create roles and policies
    create_roles_and_policies(iam_client, account_id, dev_policy_arn)
    roles = iam_client.list_roles()["Roles"]
    assert len(roles) == 2
    role_names = [role["RoleName"] for role in roles]
    assert dev_role_name in role_names
    assert user_role_name in role_names

    # 2. Create IAM user
    create_iam_user(iam_client)
    users = iam_client.list_users()["Users"]
    assert len(users) == 1
    assert users[0]["UserName"] == iam_user_name

    # 3. Assume Dev role and create S3 resources
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{dev_role_name}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client(
        "s3",
        aws_access_key_id=dev_credentials["AccessKeyId"],
        aws_secret_access_key=dev_credentials["SecretAccessKey"],
        aws_session_token=dev_credentials["SessionToken"],
    )
    create_s3_resources(s3_dev_client)

    # Verify bucket creation
    buckets = s3_dev_client.list_buckets()["Buckets"]
    assert len(buckets) == 1
    assert buckets[0]["Name"] == bucket_name

    # Verify object creation
    objects = s3_dev_client.list_objects_v2(Bucket=bucket_name)["Contents"]
    assert len(objects) == 3
    object_keys = [obj["Key"] for obj in objects]
    assert "assignment1.txt" in object_keys
    assert "assignment2.txt" in object_keys
    assert "recording1.jpg" in object_keys

    # 4. Assume User role, list objects, and compute size
    user_role_arn = f"arn:aws:iam::{account_id}:role/{user_role_name}"
    user_credentials = assume_role(sts_client, user_role_arn, "UserSession")
    s3_user_client = boto3.client(
        "s3",
        aws_access_key_id=user_credentials["AccessKeyId"],
        aws_secret_access_key=user_credentials["SecretAccessKey"],
        aws_session_token=user_credentials["SessionToken"],
    )

    # Moto's S3 implementation doesn't perfectly mimic IAM policy enforcement for cross-account access.
    # We will directly test the function's logic.
    total_size = list_and_compute_size(s3_user_client)

    # Calculate expected size
    size1 = os.path.getsize("assignment1.txt")
    size2 = os.path.getsize("assignment2.txt")
    expected_size = size1 + size2
    assert total_size == expected_size

    # 5. Assume Dev role again and clean up
    cleanup_s3_resources(s3_dev_client)

    # Verify cleanup
    try:
        s3_dev_client.head_bucket(Bucket=bucket_name)
        assert False, "Bucket should have been deleted"
    except s3_dev_client.exceptions.ClientError as e:
        assert e.response["Error"]["Code"] == "404"

    # Verify objects are gone
    response = s3_client.list_buckets()
    assert bucket_name not in [b['Name'] for b in response.get('Buckets', [])]
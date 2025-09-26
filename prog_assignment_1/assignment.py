# Boto3 script for AWS IAM and S3 operations
import boto3
import json
import time
import os

# Create a unique bucket name
bucket_name = f"prog-assignment-1-bucket-{int(time.time())}"
iam_user_name = "prog-assignment-1-user"
dev_role_name = "Dev"
user_role_name = "User"


def create_roles_and_policies(iam_client, account_id, dev_policy_arn):
    """Creates IAM roles and attaches the necessary policies."""
    print("Creating IAM roles and policies...")

    # Trust policy for IAM roles
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }

    # Create Dev role with S3 full access
    try:
        iam_client.create_role(
            RoleName=dev_role_name, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam_client.attach_role_policy(
            RoleName=dev_role_name,
            PolicyArn=dev_policy_arn,
        )
        print(f"Role '{dev_role_name}' created with S3 full access.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Role '{dev_role_name}' already exists.")

    # Create User role with S3 read-only access
    user_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetObject"],
                "Resource": "*",
            }
        ],
    }
    try:
        iam_client.create_role(
            RoleName=user_role_name, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam_client.put_role_policy(
            RoleName=user_role_name,
            PolicyName="S3ListAndGet",
            PolicyDocument=json.dumps(user_policy),
        )
        print(f"Role '{user_role_name}' created with S3 list/get access.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Role '{user_role_name}' already exists.")


def create_iam_user(iam_client):
    """Creates an IAM user."""
    print(f"Creating IAM user '{iam_user_name}'...")
    try:
        iam_client.create_user(UserName=iam_user_name)
        print(f"User '{iam_user_name}' created.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"User '{iam_user_name}' already exists.")


def assume_role(sts_client, role_arn, role_session_name):
    """Assumes an IAM role and returns temporary credentials."""
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=role_session_name
    )
    return assumed_role_object["Credentials"]


def create_s3_resources(s3_dev_client):
    """Creates S3 bucket and uploads objects."""
    print(f"Creating S3 bucket: {bucket_name}")
    s3_dev_client.create_bucket(Bucket=bucket_name)

    print("Uploading objects to the bucket...")
    s3_dev_client.upload_file("assignment1.txt", bucket_name, "assignment1.txt")
    s3_dev_client.upload_file("assignment2.txt", bucket_name, "assignment2.txt")
    s3_dev_client.upload_file("recording1.jpg", bucket_name, "recording1.jpg")
    print("Objects uploaded successfully.")


def list_and_compute_size(s3_user_client):
    """Lists objects with a prefix and computes their total size."""
    print("Finding objects with prefix 'assignment' and computing total size...")
    total_size = 0
    response = s3_user_client.list_objects_v2(Bucket=bucket_name, Prefix="assignment")
    if "Contents" in response:
        for obj in response["Contents"]:
            print(f" - Found object: {obj['Key']}, Size: {obj['Size']} bytes")
            total_size += obj["Size"]
    print(f"Total size of objects with prefix 'assignment': {total_size} bytes")
    return total_size


def cleanup_s3_resources(s3_dev_client):
    """Deletes all objects from the bucket and the bucket itself."""
    print("Deleting all objects from the bucket...")
    response = s3_dev_client.list_objects_v2(Bucket=bucket_name)
    if "Contents" in response:
        objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
        s3_dev_client.delete_objects(
            Bucket=bucket_name, Delete={"Objects": objects_to_delete}
        )

    print(f"Deleting bucket: {bucket_name}")
    s3_dev_client.delete_bucket(Bucket=bucket_name)
    print("Cleanup complete.")


def main():
    """Main function to execute the assignment steps."""
    iam_client = boto3.client("iam")
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity().get("Account")

    # Create dummy files for upload
    with open("assignment1.txt", "w") as f:
        f.write("Empty Assignment 1")
    with open("assignment2.txt", "w") as f:
        f.write("Empty Assignment 2")
    with open("recording1.jpg", "w") as f:
        f.write("dummy_image_data")

    # Step 1 & 2: Create IAM roles and attach policies
    dev_policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
    create_roles_and_policies(iam_client, account_id, dev_policy_arn)

    # Step 3: Create an IAM user
    create_iam_user(iam_client)

    # Step 4: Assume Dev role and manage S3 resources
    print("\nAssuming 'Dev' role to manage S3 resources...")
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{dev_role_name}"
    dev_credentials = assume_role(sts_client, dev_role_arn, "DevSession")
    s3_dev_client = boto3.client(
        "s3",
        aws_access_key_id=dev_credentials["AccessKeyId"],
        aws_secret_access_key=dev_credentials["SecretAccessKey"],
        aws_session_token=dev_credentials["SessionToken"],
    )
    create_s3_resources(s3_dev_client)

    # Step 5: Assume User role and list objects
    print("\nAssuming 'User' role to list objects...")
    user_role_arn = f"arn:aws:iam::{account_id}:role/{user_role_name}"
    user_credentials = assume_role(sts_client, user_role_arn, "UserSession")
    s3_user_client = boto3.client(
        "s3",
        aws_access_key_id=user_credentials["AccessKeyId"],
        aws_secret_access_key=user_credentials["SecretAccessKey"],
        aws_session_token=user_credentials["SessionToken"],
    )
    list_and_compute_size(s3_user_client)

    # Step 6: Assume Dev role again and clean up
    print("\nAssuming 'Dev' role again for cleanup...")
    dev_cleanup_credentials = assume_role(sts_client, dev_role_arn, "DevCleanupSession")
    s3_dev_cleanup_client = boto3.client(
        "s3",
        aws_access_key_id=dev_cleanup_credentials["AccessKeyId"],
        aws_secret_access_key=dev_cleanup_credentials["SecretAccessKey"],
        aws_session_token=dev_cleanup_credentials["SessionToken"],
    )
    cleanup_s3_resources(s3_dev_cleanup_client)

    # Clean up local files
    os.remove("assignment1.txt")
    os.remove("assignment2.txt")
    os.remove("recording1.jpg")

    print("Assignment completed successfully!")


if __name__ == "__main__":
    main()
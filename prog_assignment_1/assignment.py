# Boto3 script for AWS IAM and S3 operations
import boto3
import json
import time
import os

# --- Constants ---
# Using a fixed but unique name for the bucket to ease cleanup in case of script failure.
# In a real-world scenario, a more robust naming or tracking mechanism would be used.
BUCKET_NAME = f"cs6620-prog-assignment-1-bucket-{int(time.time())}"
IAM_USER_NAME = "prog-assignment-1-user"
DEV_ROLE_NAME = "Dev"
USER_ROLE_NAME = "User"


def create_roles_and_policies(iam_client, account_id, dev_policy_arn):
    """Creates IAM roles and attaches the necessary policies."""
    print("Creating IAM roles and policies...")
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

    try:
        iam_client.create_role(
            RoleName=DEV_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam_client.attach_role_policy(RoleName=DEV_ROLE_NAME, PolicyArn=dev_policy_arn)
        print(f"Role '{DEV_ROLE_NAME}' created with S3 full access.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Role '{DEV_ROLE_NAME}' already exists.")

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
            RoleName=USER_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam_client.put_role_policy(
            RoleName=USER_ROLE_NAME,
            PolicyName="S3ListAndGet",
            PolicyDocument=json.dumps(user_policy),
        )
        print(f"Role '{USER_ROLE_NAME}' created with S3 list/get access.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"Role '{USER_ROLE_NAME}' already exists.")


def create_iam_user(iam_client):
    """Creates an IAM user."""
    print(f"Creating IAM user '{IAM_USER_NAME}'...")
    try:
        iam_client.create_user(UserName=IAM_USER_NAME)
        print(f"User '{IAM_USER_NAME}' created.")
    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"User '{IAM_USER_NAME}' already exists.")


def add_user_permissions(iam_client, account_id):
    """Attaches a policy to the user to allow assuming roles."""
    print(f"Attaching assume-role policy to user '{IAM_USER_NAME}'...")
    dev_role_arn = f"arn:aws:iam::{account_id}:role/{DEV_ROLE_NAME}"
    user_role_arn = f"arn:aws:iam::{account_id}:role/{USER_ROLE_NAME}"
    assume_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": "sts:AssumeRole",
                "Resource": [dev_role_arn, user_role_arn],
            }
        ],
    }
    try:
        iam_client.put_user_policy(
            UserName=IAM_USER_NAME,
            PolicyName="AllowAssumeDevUserRoles",
            PolicyDocument=json.dumps(assume_policy),
        )
        print("Policy attached successfully.")
    except Exception as e:
        print(f"Could not attach policy to user '{IAM_USER_NAME}': {e}")


def assume_role(sts_client, role_arn, role_session_name):
    """Assumes an IAM role and returns temporary credentials."""
    assumed_role_object = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=role_session_name
    )
    return assumed_role_object["Credentials"]


def create_s3_resources(s3_dev_client):
    """Creates S3 bucket (region-aware) and uploads objects."""
    print(f"Creating S3 bucket: {BUCKET_NAME}")
    region = s3_dev_client.meta.region_name
    try:
        if region == "us-east-1":
            s3_dev_client.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3_dev_client.create_bucket(
                Bucket=BUCKET_NAME,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"Bucket '{BUCKET_NAME}' created in region '{region}'.")
    except s3_dev_client.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket '{BUCKET_NAME}' already exists and is owned by you.")
    
    print("Uploading objects to the bucket...")
    s3_dev_client.upload_file("assignment1.txt", BUCKET_NAME, "assignment1.txt")
    s3_dev_client.upload_file("assignment2.txt", BUCKET_NAME, "assignment2.txt")
    s3_dev_client.upload_file("recording1.jpg", BUCKET_NAME, "recording1.jpg")
    print("Objects uploaded successfully.")


def list_and_compute_size(s3_user_client):
    """Lists objects with a prefix and computes their total size."""
    print("Finding objects with prefix 'assignment' and computing total size...")
    total_size = 0
    response = s3_user_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="assignment")
    if "Contents" in response:
        for obj in response["Contents"]:
            print(f" - Found object: {obj['Key']}, Size: {obj['Size']} bytes")
            total_size += obj["Size"]
    print(f"Total size of objects with prefix 'assignment': {total_size} bytes")
    return total_size


def cleanup_s3_resources(s3_dev_client):
    """Deletes all objects from the bucket and the bucket itself."""
    print("\nCleaning up S3 resources...")
    try:
        print("Deleting all objects from the bucket...")
        response = s3_dev_client.list_objects_v2(Bucket=BUCKET_NAME)
        if "Contents" in response:
            objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
            s3_dev_client.delete_objects(
                Bucket=BUCKET_NAME, Delete={"Objects": objects_to_delete}
            )
        print(f"Deleting bucket: {BUCKET_NAME}")
        s3_dev_client.delete_bucket(Bucket=BUCKET_NAME)
        print("S3 cleanup complete.")
    except Exception as e:
        print(f"Could not clean up S3 resources: {e}")


def cleanup_iam_resources(iam_client, dev_policy_arn):
    """Detaches policies and deletes the IAM user and roles."""
    print("\nCleaning up IAM resources...")
    try:
        iam_client.detach_role_policy(RoleName=DEV_ROLE_NAME, PolicyArn=dev_policy_arn)
        iam_client.delete_role(RoleName=DEV_ROLE_NAME)
        print(f"Role '{DEV_ROLE_NAME}' deleted.")
    except Exception as e:
        print(f"Could not delete role '{DEV_ROLE_NAME}': {e}")

    try:
        iam_client.delete_role_policy(RoleName=USER_ROLE_NAME, PolicyName="S3ListAndGet")
        iam_client.delete_role(RoleName=USER_ROLE_NAME)
        print(f"Role '{USER_ROLE_NAME}' deleted.")
    except Exception as e:
        print(f"Could not delete role '{USER_ROLE_NAME}': {e}")

    try:
        iam_client.delete_user_policy(UserName=IAM_USER_NAME, PolicyName="AllowAssumeDevUserRoles")
        iam_client.delete_user(UserName=IAM_USER_NAME)
        print(f"User '{IAM_USER_NAME}' deleted.")
    except Exception as e:
        print(f"Could not delete user '{IAM_USER_NAME}': {e}")


def main():
    """Main function to execute the assignment steps."""
    # Use a specific region for consistency; can be changed or read from env
    region = "us-east-1"
    iam_client = boto3.client("iam", region_name=region)
    sts_client = boto3.client("sts", region_name=region)
    s3_client = boto3.client("s3", region_name=region)
    account_id = sts_client.get_caller_identity().get("Account")

    # Create dummy files for upload
    with open("assignment1.txt", "w") as f: f.write("Empty Assignment 1")
    with open("assignment2.txt", "w") as f: f.write("Empty Assignment 2")
    with open("recording1.jpg", "w") as f: f.write("dummy_image_data")

    # Step 1 & 2: Create IAM roles and user
    dev_policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
    create_roles_and_policies(iam_client, account_id, dev_policy_arn)
    create_iam_user(iam_client)
    add_user_permissions(iam_client, account_id)

    # Step 3 & 4: Assume Dev role and manage S3 resources
    print("\n--- Assuming 'Dev' role to manage S3 resources ---")
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

    # Step 5: Assume User role and list objects
    print("\n--- Assuming 'User' role to list objects ---")
    user_role_arn = f"arn:aws:iam::{account_id}:role/{USER_ROLE_NAME}"
    user_credentials = assume_role(sts_client, user_role_arn, "UserSession")
    s3_user_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=user_credentials["AccessKeyId"],
        aws_secret_access_key=user_credentials["SecretAccessKey"],
        aws_session_token=user_credentials["SessionToken"],
    )
    list_and_compute_size(s3_user_client)

    # Step 6: Assume Dev role again and clean up S3
    print("\n--- Assuming 'Dev' role again for S3 cleanup ---")
    dev_cleanup_credentials = assume_role(sts_client, dev_role_arn, "DevCleanupSession")
    s3_dev_cleanup_client = boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=dev_cleanup_credentials["AccessKeyId"],
        aws_secret_access_key=dev_cleanup_credentials["SecretAccessKey"],
        aws_session_token=dev_cleanup_credentials["SessionToken"],
    )
    cleanup_s3_resources(s3_dev_cleanup_client)

    # Final Cleanup: IAM resources
    cleanup_iam_resources(iam_client, dev_policy_arn)

    # Clean up local files
    os.remove("assignment1.txt")
    os.remove("assignment2.txt")
    os.remove("recording1.jpg")

    print("\nAssignment completed successfully!")


if __name__ == "__main__":
    main()
# setup_resources.py
"""
Create S3 bucket and DynamoDB table for CS6620 assignment.
Run locally with AWS credentials configured (AWS CLI profile or env vars).
"""

import boto3
import botocore
import time

REGION = "us-east-1"           # <-- change as needed
BUCKET = "testbucket-PLACEHOLDER-UNIQUE"  # <-- change to a globally unique name
TABLE_NAME = "S3-object-size-history"

s3 = boto3.client("s3", region_name=REGION)
ddb = boto3.client("dynamodb", region_name=REGION)

def create_bucket():
    try:
        print(f"Creating bucket: {BUCKET} in region {REGION} ...")
        if REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET)
        else:
            s3.create_bucket(Bucket=BUCKET,
                             CreateBucketConfiguration={'LocationConstraint': REGION})
        print("Bucket created:", BUCKET)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print("Bucket already exists and is owned by you.")
        else:
            print("Bucket create error:", e)
            raise

def create_table():
    try:
        print(f"Creating DynamoDB table: {TABLE_NAME} (PAY_PER_REQUEST) ...")
        resp = ddb.create_table(
            TableName=TABLE_NAME,
            AttributeDefinitions=[
                {'AttributeName': 'bucket_name', 'AttributeType': 'S'},
                {'AttributeName': 'ts', 'AttributeType': 'N'},
                {'AttributeName': 'size', 'AttributeType': 'N'}
            ],
            KeySchema=[
                {'AttributeName': 'bucket_name', 'KeyType': 'HASH'},
                {'AttributeName': 'ts', 'KeyType': 'RANGE'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'bucket_size_index',
                    'KeySchema': [
                        {'AttributeName': 'bucket_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'size', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print("Table creation initiated:", resp['TableDescription']['TableName'])
        waiter = ddb.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)
        print("DynamoDB table active.")
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Table already exists.")
        else:
            print("Table create error:", e)
            raise

if __name__ == "__main__":
    create_bucket()
    create_table()
    print("Setup complete.")
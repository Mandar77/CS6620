# size_tracking_lambda.py
import boto3
import time
import os
import traceback

TABLE_NAME = os.environ.get("DDB_TABLE", "S3-object-size-history")

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Triggered by S3 events (ObjectCreated:Object*, ObjectRemoved:*)
    Computes total size and number of objects in bucket, then writes an item to DynamoDB.
    """
    try:
        records = event.get("Records", [])
        if not records:
            return {"status": "no_records"}
        # assume bucket is the bucket in the first record
        bucket = records[0]["s3"]["bucket"]["name"]
        # compute total size using list_objects_v2 paginator
        paginator = s3.get_paginator("list_objects_v2")
        total_size = 0
        total_count = 0
        for page in paginator.paginate(Bucket=bucket):
            for obj in page.get("Contents", []):
                total_count += 1
                total_size += int(obj.get("Size", 0))
        ts = int(time.time() * 1000)
        item = {
            "bucket_name": bucket,
            "ts": ts,
            "size": total_size,
            "object_count": total_count
        }
        table.put_item(Item=item)
        print("Wrote to DDB:", item)
        return {"status": "ok", "item": item}
    except Exception as e:
        print("Error in size_tracking_lambda:", e)
        traceback.print_exc()
        raise
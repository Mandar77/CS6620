# size_tracking_lambda.py
import boto3
import time
import os
import traceback

TABLE_NAME = os.environ.get("DDB_TABLE", "S3-object-size-history")
# optional: region via env AWS_REGION; boto3 will use default otherwise
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(TABLE_NAME)

def safe_list_objects_total(bucket, attempts=3, backoff_s=0.5):
    for attempt in range(1, attempts+1):
        try:
            paginator = s3.get_paginator("list_objects_v2")
            total_size = 0
            total_count = 0
            for page in paginator.paginate(Bucket=bucket):
                for obj in page.get("Contents", []):
                    total_count += 1
                    total_size += int(obj.get("Size", 0))
            return total_size, total_count
        except Exception as e:
            if attempt == attempts:
                raise
            time.sleep(backoff_s * attempt)
    # fallback
    return 0, 0

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
        total_size, total_count = safe_list_objects_total(bucket)
        ts = int(time.time() * 1000)  # store epoch ms
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

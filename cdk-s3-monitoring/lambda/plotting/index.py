import os
import io
import time
import boto3
import traceback
import json
from boto3.dynamodb.conditions import Key
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TABLE_NAME = os.environ.get("DDB_TABLE", "S3-object-size-history")
BUCKET = os.environ.get("BUCKET", "testbucket-mandar-cs6620")
GSI_NAME = os.environ.get("GSI_NAME", "bucket_size_index")

# AWS_REGION is automatically available as environment variable
# No need to set it manually - boto3 will use it automatically
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(TABLE_NAME)


def query_last_10_seconds(bucket):
    """Query DynamoDB for items from the last 10 seconds."""
    now_ms = int(time.time() * 1000)
    ten_sec_ago = now_ms - 10 * 1000
    resp = table.query(
        KeyConditionExpression=Key("bucket_name").eq(bucket)
        & Key("ts").between(ten_sec_ago, now_ms),
        ScanIndexForward=True,
    )
    items = resp.get("Items", [])
    # convert DynamoDB Decimal -> float/int
    xs = [float(item["ts"]) / 1000.0 for item in items]
    ys = [float(item["size"]) for item in items]
    return xs, ys


def query_max_size(bucket):
    """Query GSI to find max size ever recorded for this bucket."""
    resp = table.query(
        IndexName=GSI_NAME,
        KeyConditionExpression=Key("bucket_name").eq(bucket),
        ScanIndexForward=False,
        Limit=1,
    )
    items = resp.get("Items", [])
    if items:
        return float(items[0].get("size", 0))
    return 0.0


def make_plot(xs, ys, max_size, bucket):
    """Generate a matplotlib plot."""
    plt.figure(figsize=(8, 4))
    if xs and ys:
        plt.plot(xs, ys, marker="o", linestyle="-")
    else:
        # empty plot placeholder
        plt.plot([], [])
        plt.text(
            0.5,
            0.5,
            "No data in last 10s",
            horizontalalignment="center",
            transform=plt.gca().transAxes,
        )
    plt.axhline(
        y=max_size, linestyle="--", label=f"Historical high = {int(max_size)} bytes"
    )
    plt.title(f"Bucket size changes (last 10s) for {bucket}")
    plt.xlabel("timestamp (s)")
    plt.ylabel("size (bytes)")
    plt.legend()
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return buf


def upload_plot(buf, bucket, key):
    """Upload plot buffer to S3."""
    s3.upload_fileobj(buf, bucket, key)
    return {"bucket": bucket, "key": key}


def lambda_handler(event, context):
    """
    HTTP-triggered (API Gateway). Optional query param: ?bucket=<bucket-name>
    Produces a PNG plot and uploads to S3 as plot-<ts>.png, returns a presigned URL.
    """
    try:
        bucket = BUCKET
        # if API Gateway provides query string parameters
        qs = event.get("queryStringParameters") or {}
        if qs and qs.get("bucket"):
            bucket = qs.get("bucket")

        xs, ys = query_last_10_seconds(bucket)
        max_size = query_max_size(bucket)
        buf = make_plot(xs, ys, max_size, bucket)
        ts = int(time.time())
        key = f"plot-{ts}.png"
        upload_plot(buf, bucket, key)
        url = s3.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "s3_bucket": bucket,
                    "s3_key": key,
                    "presigned_url": url,
                }
            ),
        }
    except Exception as e:
        print("Error in plotting_lambda:", e)
        traceback.print_exc()
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
import boto3
import time
import os
import urllib.request
import json

BUCKET = os.environ.get("BUCKET", "testbucket-mandar-cs6620")
# You'll need to pass PLOTTING_API_URL via environment variable or update it after deployment
PLOTTING_API = os.environ.get("PLOTTING_API", "https://xgn5ppah0c.execute-api.us-east-1.amazonaws.com/prod/plot")

s3 = boto3.client("s3")
lambda_client = boto3.client("lambda")


def put_obj(key, content):
    """Put object in S3."""
    s3.put_object(Bucket=BUCKET, Key=key, Body=content.encode("utf-8"))
    print(f"Put {key}: {len(content)} bytes")


def delete_obj(key):
    """Delete object from S3."""
    s3.delete_object(Bucket=BUCKET, Key=key)
    print(f"Deleted {key}")


def call_plot_api():
    """Call the plotting lambda via REST API."""
    try:
        with urllib.request.urlopen(PLOTTING_API) as resp:
            data = resp.read()
            result = json.loads(data.decode("utf-8"))
            print("Plot API response:", result)
            return result
    except Exception as e:
        print("Plot API call error:", e)
        raise


def lambda_handler(event, context):
    """
    Driver lambda that orchestrates the workflow:
    1. Create assignment1.txt with "Empty Assignment 1" (19 bytes)
    2. Update assignment1.txt to "Empty Assignment 2222222222" (28 bytes)
    3. Delete assignment1.txt
    4. Create assignment2.txt with "33" (2 bytes)
    5. Call plotting API
    """
    try:
        # 1) create assignment1.txt "Empty Assignment 1" (19 bytes)
        put_obj("assignment1.txt", "Empty Assignment 1")
        time.sleep(3)

        # 2) update assignment1.txt -> "Empty Assignment 2222222222" (28 bytes)
        put_obj("assignment1.txt", "Empty Assignment 2222222222")
        time.sleep(3)

        # 3) delete assignment1.txt
        delete_obj("assignment1.txt")
        time.sleep(3)

        # 4) create assignment2.txt with "33" (2 bytes)
        put_obj("assignment2.txt", "33")
        time.sleep(3)

        # 5) Finally call plotting API
        api_result = call_plot_api()

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "status": "done",
                    "api_response": api_result,
                }
            ),
        }
    except Exception as e:
        print("Error in driver_lambda:", e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
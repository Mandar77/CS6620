# driver_lambda.py
import boto3
import time
import os
import urllib.request

BUCKET = os.environ.get("BUCKET", "testbucket-mandar-cs6620")
PLOTTING_API = os.environ.get("PLOTTING_API", "https://REPLACE_WITH_YOUR_API.execute-api.REGION.amazonaws.com/prod/plot")

s3 = boto3.client("s3")

def put_obj(key, content):
    s3.put_object(Bucket=BUCKET, Key=key, Body=content.encode('utf-8'))
    print(f"Put {key}: {len(content)} bytes")

def delete_obj(key):
    s3.delete_object(Bucket=BUCKET, Key=key)
    print(f"Deleted {key}")

def call_plot_api():
    try:
        with urllib.request.urlopen(PLOTTING_API) as resp:
            data = resp.read()
            print("Plot API response:", data.decode('utf-8'))
    except Exception as e:
        print("Plot API call error:", e)

def lambda_handler(event, context):
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
    # Finally call plotting API
    call_plot_api()
    return {"status": "done"}
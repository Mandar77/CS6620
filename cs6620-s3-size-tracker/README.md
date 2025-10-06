# CS6620 - S3 Bucket Size Tracker

## Files
- setup_resources.py          # create S3 bucket & DynamoDB table
- size_tracking_lambda.py     # Lambda handler (S3 event -> DDB)
- plotting_lambda.py          # Lambda handler (HTTP -> plot -> S3)
- driver_lambda.py            # Lambda handler to generate S3 events and call plotting API
- requirements.txt            # dependencies for plotting lambda / layer
- Dockerfile + build_layer.sh # build matplotlib Lambda layer (local Docker build)
- README.md

## Quick run
1. Edit `setup_resources.py` and set REGION and BUCKET to your values.
2. Run `python3 setup_resources.py` to create bucket and DynamoDB table.
3. Create Lambda functions in AWS Console:
   - `size_tracking_lambda` with handler `size_tracking_lambda.lambda_handler`, set env `DDB_TABLE=S3-object-size-history`. Add S3 trigger for your bucket (All object create and delete events).
   - `plotting_lambda` with handler `plotting_lambda.lambda_handler`, set env `DDB_TABLE`, `BUCKET`, `GSI_NAME` and attach matplotlib layer (see below).
   - `driver_lambda` with handler `driver_lambda.lambda_handler`, set env `BUCKET` and `PLOTTING_API`.
4. Build and upload the matplotlib layer:
   - `./build_layer.sh` (requires Docker)
   - Upload `/tmp/matplotlib_layer.zip` to AWS Lambda Layers; attach to `plotting_lambda`.
5. Create API Gateway (HTTP) to invoke `plotting_lambda` (GET).
6. Invoke `driver_lambda` manually (AWS Console) to run the demo.
7. Download the generated plot from S3; TAs will check DynamoDB items.

## Notes
- Replace placeholders (bucket names, ARNs) before deployment.
- For large buckets listing all objects can be slow. For this assignment with a few objects, `list_objects_v2` is fine.
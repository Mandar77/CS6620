# from aws_cdk import (
#     aws_lambda as lambda_,
#     aws_dynamodb as dynamodb,
#     aws_s3 as s3,
#     aws_s3_notifications as s3_notifications,
#     aws_iam as iam,
#     Stack,
#     Duration,
# )
# from constructs import Construct
# import os


# class LambdaStack(Stack):
#     def __init__(
#         self,
#         scope: Construct,
#         id: str,
#         bucket: s3.Bucket,
#         table: dynamodb.Table,
#         **kwargs
#     ):
#         super().__init__(scope, id, **kwargs)

#         self.bucket = bucket
#         self.table = table

#         # Create Lambda execution role
#         lambda_role = iam.Role(
#             self,
#             "LambdaExecutionRole",
#             assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
#             managed_policies=[
#                 iam.ManagedPolicy.from_aws_managed_policy_name(
#                     "service-role/AWSLambdaBasicExecutionRole"
#                 ),
#             ],
#         )

#         # Add S3 permissions using inline policy
#         lambda_role.add_to_policy(
#             iam.PolicyStatement(
#                 effect=iam.Effect.ALLOW,
#                 actions=[
#                     "s3:GetObject",
#                     "s3:PutObject",
#                     "s3:DeleteObject",
#                     "s3:ListBucket",
#                 ],
#                 resources=[
#                     self.bucket.bucket_arn,
#                     self.bucket.arn_for_objects("*"),
#                 ],
#             )
#         )

#         # Add DynamoDB permissions
#         self.table.grant_read_write_data(lambda_role)

#         # Size-Tracking Lambda
#         self.size_tracking_lambda = lambda_.Function(
#             self,
#             "SizeTrackingLambda",
#             runtime=lambda_.Runtime.PYTHON_3_11,
#             handler="index.lambda_handler",
#             code=lambda_.Code.from_asset(
#                 path=os.path.join(os.path.dirname(__file__), "../lambda/size_tracking"),
#                 exclude=["*.pyc", "__pycache__"],
#             ),
#             role=lambda_role,
#             environment={
#                 "DDB_TABLE": self.table.table_name,
#                 "BUCKET": self.bucket.bucket_name,
#             },
#             timeout=Duration.seconds(60),
#         )

#         # Plotting Lambda (with matplotlib layer)
#         plotting_layers = []
#         try:
#             matplotlib_layer = self._get_matplotlib_layer()
#             if matplotlib_layer:
#                 plotting_layers.append(matplotlib_layer)
#         except Exception as e:
#             print(f"Warning: Could not load matplotlib layer: {e}")

#         self.plotting_lambda = lambda_.Function(
#             self,
#             "PlottingLambda",
#             runtime=lambda_.Runtime.PYTHON_3_11,
#             handler="index.lambda_handler",
#             code=lambda_.Code.from_asset(
#                 path=os.path.join(os.path.dirname(__file__), "../lambda/plotting"),
#                 exclude=["*.pyc", "__pycache__"],
#             ),
#             role=lambda_role,
#             environment={
#                 "DDB_TABLE": self.table.table_name,
#                 "BUCKET": self.bucket.bucket_name,
#                 "GSI_NAME": "bucket_size_index",
#             },
#             timeout=Duration.seconds(60),
#             layers=plotting_layers if plotting_layers else None,
#             memory_size=512,  # Increase memory for matplotlib
#         )

#         # Driver Lambda
#         self.driver_lambda = lambda_.Function(
#             self,
#             "DriverLambda",
#             runtime=lambda_.Runtime.PYTHON_3_11,
#             handler="index.lambda_handler",
#             code=lambda_.Code.from_asset(
#                 path=os.path.join(os.path.dirname(__file__), "../lambda/driver"),
#                 exclude=["*.pyc", "__pycache__"],
#             ),
#             role=lambda_role,
#             environment={
#                 "BUCKET": self.bucket.bucket_name,
#             },
#             timeout=Duration.seconds(120),
#         )

#         # Allow driver lambda to invoke plotting lambda
#         self.plotting_lambda.grant_invoke(self.driver_lambda)

#         # Add S3 event notifications to trigger size-tracking lambda
#         # This must be done in LambdaStack to avoid cyclic dependencies
#         self.bucket.add_event_notification(
#             s3.EventType.OBJECT_CREATED,
#             s3_notifications.LambdaDestination(self.size_tracking_lambda),
#         )
#         # Use OBJECT_REMOVED instead of OBJECT_DELETED
#         self.bucket.add_event_notification(
#             s3.EventType.OBJECT_REMOVED,
#             s3_notifications.LambdaDestination(self.size_tracking_lambda),
#         )

#         # Export lambda names for API Gateway
#         self.plotting_lambda_name = self.plotting_lambda.function_name

#     def _get_matplotlib_layer(self):
#         """
#         Get your existing matplotlib layer from Assignment 2.
#         You must manually create this layer first using:
#         https://docs.aws.amazon.com/lambda/latest/dg/python-layers.html
        
#         To create the layer:
#         1. Create a folder: python/lib/python3.11/site-packages/
#         2. pip install matplotlib -t python/lib/python3.11/site-packages/
#         3. Zip the python folder
#         4. Upload to Lambda Layers in AWS console
#         5. Note the ARN and update MATPLOTLIB_LAYER_ARN below
#         """
#         # Update this ARN with your actual matplotlib layer ARN
#         # Format: arn:aws:lambda:REGION:ACCOUNT:layer:LAYER_NAME:VERSION
#         matplotlib_layer_arn = f"arn:aws:lambda:us-east-1:696791035505:layer:matplotlib-layer:1"
        
#         try:
#             return lambda_.LayerVersion.from_layer_version_arn(
#                 self, "MatplotlibLayer", matplotlib_layer_arn
#             )
#         except Exception:
#             print(f"Warning: Matplotlib layer not found at {matplotlib_layer_arn}")
#             print("The plotting lambda will attempt to use matplotlib if available in the function package")
#             return None
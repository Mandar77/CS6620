# from aws_cdk import (
#     aws_s3 as s3,
#     aws_dynamodb as dynamodb,
#     aws_lambda as lambda_,
#     aws_lambda_event_sources as lambda_events,
#     aws_iam as iam,
#     Stack,
#     Duration,
#     RemovalPolicy,
#     CfnOutput,
# )
# from constructs import Construct
# import os


# class ComputeStack(Stack):
#     def __init__(self, scope: Construct, id: str, **kwargs):
#         super().__init__(scope, id, **kwargs)

#         # ====== STORAGE RESOURCES ======
        
#         self.bucket = s3.Bucket(
#             self,
#             "S3MonitoringBucket",
#             block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
#             versioned=False,
#             removal_policy=RemovalPolicy.DESTROY,
#             auto_delete_objects=True,
#         )

#         self.table = dynamodb.Table(
#             self,
#             "S3ObjectSizeHistory",
#             partition_key=dynamodb.Attribute(
#                 name="bucket_name",
#                 type=dynamodb.AttributeType.STRING,
#             ),
#             sort_key=dynamodb.Attribute(
#                 name="ts",
#                 type=dynamodb.AttributeType.NUMBER,
#             ),
#             billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
#             removal_policy=RemovalPolicy.DESTROY,
#         )

#         self.table.add_global_secondary_index(
#             index_name="bucket_size_index",
#             partition_key=dynamodb.Attribute(
#                 name="bucket_name",
#                 type=dynamodb.AttributeType.STRING,
#             ),
#             sort_key=dynamodb.Attribute(
#                 name="size",
#                 type=dynamodb.AttributeType.NUMBER,
#             ),
#             projection_type=dynamodb.ProjectionType.ALL,
#         )

#         # ====== LAMBDA EXECUTION ROLE ======

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

#         # ====== SIZE TRACKING LAMBDA ======
        
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

#         # Grant S3 read access
#         self.bucket.grant_read(self.size_tracking_lambda)
        
#         # Grant DynamoDB write access
#         self.table.grant_write_data(self.size_tracking_lambda)

#         # Add S3 event source using addEventSource (THIS IS KEY - like your friend's TS code)
#         self.size_tracking_lambda.add_event_source(
#             lambda_events.S3EventSource(
#                 self.bucket,
#                 events=[
#                     s3.EventType.OBJECT_CREATED,
#                     s3.EventType.OBJECT_REMOVED,
#                 ],
#             )
#         )

#         # ====== PLOTTING LAMBDA ======

#         plotting_layers = []
#         try:
#             matplotlib_layer = self._get_matplotlib_layer()
#             if matplotlib_layer:
#                 plotting_layers.append(matplotlib_layer)
#         except Exception:
#             pass

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
#             memory_size=512,
#         )

#         # Grant S3 write access
#         self.bucket.grant_write(self.plotting_lambda)
        
#         # Grant DynamoDB read access
#         self.table.grant_read_data(self.plotting_lambda)

#         # ====== DRIVER LAMBDA ======

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

#         # Grant S3 write access
#         self.bucket.grant_write(self.driver_lambda)
        
#         # Driver can invoke plotting lambda
#         self.plotting_lambda.grant_invoke(self.driver_lambda)

#         # ====== OUTPUTS ======

#         CfnOutput(
#             self,
#             "PlottingLambdaArn",
#             value=self.plotting_lambda.function_arn,
#             export_name="PlottingLambdaArn",
#         )

#         CfnOutput(
#             self,
#             "BucketName",
#             value=self.bucket.bucket_name,
#         )

#         CfnOutput(
#             self,
#             "TableName",
#             value=self.table.table_name,
#         )

#         CfnOutput(
#             self,
#             "DriverLambdaName",
#             value=self.driver_lambda.function_name,
#         )

#         CfnOutput(
#             self,
#             "SizeTrackingLambdaName",
#             value=self.size_tracking_lambda.function_name,
#         )

#     def _get_matplotlib_layer(self):
#         """Get matplotlib layer from Assignment 2."""
#         matplotlib_layer_arn = f"arn:aws:lambda:{self.region}:{self.account}:layer:matplotlib-layer:1"
#         try:
#             return lambda_.LayerVersion.from_layer_version_arn(
#                 self, "MatplotlibLayer", matplotlib_layer_arn
#             )
#         except Exception:
#             return None
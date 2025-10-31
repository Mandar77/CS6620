# from aws_cdk import (
#     aws_s3 as s3,
#     aws_dynamodb as dynamodb,
#     Stack,
#     RemovalPolicy,
# )
# from constructs import Construct


# class StorageStack(Stack):
#     def __init__(self, scope: Construct, id: str, **kwargs):
#         super().__init__(scope, id, **kwargs)

#         # S3 Bucket - CDK generates unique name automatically
#         self.bucket = s3.Bucket(
#             self,
#             "S3MonitoringBucket",
#             block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
#             versioned=False,
#             removal_policy=RemovalPolicy.DESTROY,
#             auto_delete_objects=True,
#         )

#         # DynamoDB Table
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

#         # Global Secondary Index for querying max size across all buckets
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

#         # Expose as properties
#         self.bucket_name = self.bucket.bucket_name
#         self.table_name = self.table.table_name
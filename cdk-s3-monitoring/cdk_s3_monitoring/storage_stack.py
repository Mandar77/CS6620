from aws_cdk import (
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_lambda_event_sources as lambda_events,
    aws_iam as iam,
    Stack,
    Duration,
    RemovalPolicy,
)
from constructs import Construct
import os


class StorageStack(Stack):
    """Storage stack containing S3 bucket, DynamoDB table, and Size Tracking Lambda with S3 events"""

    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # ====== S3 BUCKET ======
        self.bucket = s3.Bucket(
            self,
            "S3MonitoringBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ====== DYNAMODB TABLE ======
        self.table = dynamodb.Table(
            self,
            "S3ObjectSizeHistory",
            partition_key=dynamodb.Attribute(
                name="bucket_name",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="ts",
                type=dynamodb.AttributeType.NUMBER,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        self.table.add_global_secondary_index(
            index_name="bucket_size_index",
            partition_key=dynamodb.Attribute(
                name="bucket_name",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="size",
                type=dynamodb.AttributeType.NUMBER,
            ),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # ====== LAMBDA EXECUTION ROLE ======
        lambda_role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # ====== SIZE TRACKING LAMBDA (with S3 events) ======
        size_tracking_lambda = lambda_.Function(
            self,
            "SizeTrackingLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "../lambda/size_tracking"),
                exclude=["*.pyc", "__pycache__"],
            ),
            role=lambda_role,
            environment={
                "DDB_TABLE": self.table.table_name,
                "BUCKET": self.bucket.bucket_name,
            },
            timeout=Duration.seconds(60),
        )

        # Grant S3 read access
        self.bucket.grant_read(size_tracking_lambda)

        # Grant DynamoDB write access
        self.table.grant_write_data(size_tracking_lambda)

        # Add S3 event source - THIS IS IN STORAGE STACK, NOT LAMBDA STACK
        size_tracking_lambda.add_event_source(
            lambda_events.S3EventSource(
                self.bucket,
                events=[
                    s3.EventType.OBJECT_CREATED,
                    s3.EventType.OBJECT_REMOVED,
                ],
            )
        )

from aws_cdk import (
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_iam as iam,
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct
import os


class ComputeStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # ====== STORAGE RESOURCES ======
        
        self.bucket = s3.Bucket(
            self,
            "S3MonitoringBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

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

        # ====== LAMBDA EXECUTION ROLE WITH INLINE POLICY ======
        # Create role first WITHOUT policies

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

        # Add inline policy - this breaks the dependency cycle
        policy = iam.Policy(
            self,
            "S3DynamoDBAccessPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                    ],
                    resources=[
                        self.bucket.bucket_arn,
                        self.bucket.arn_for_objects("*"),
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:ConditionCheckItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:DescribeTable",
                        "dynamodb:GetItem",
                        "dynamodb:GetRecords",
                        "dynamodb:GetShardIterator",
                        "dynamodb:PutItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:UpdateItem",
                    ],
                    resources=[
                        self.table.table_arn,
                        self.table.table_arn + "/index/*",
                    ],
                ),
            ],
        )
        
        lambda_role.attach_inline_policy(policy)

        # ====== CREATE LAMBDAS ======

        self.size_tracking_lambda = lambda_.Function(
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

        plotting_layers = []
        try:
            matplotlib_layer = self._get_matplotlib_layer()
            if matplotlib_layer:
                plotting_layers.append(matplotlib_layer)
        except Exception:
            pass

        self.plotting_lambda = lambda_.Function(
            self,
            "PlottingLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "../lambda/plotting"),
                exclude=["*.pyc", "__pycache__"],
            ),
            role=lambda_role,
            environment={
                "DDB_TABLE": self.table.table_name,
                "BUCKET": self.bucket.bucket_name,
                "GSI_NAME": "bucket_size_index",
            },
            timeout=Duration.seconds(60),
            layers=plotting_layers if plotting_layers else None,
            memory_size=512,
        )

        self.driver_lambda = lambda_.Function(
            self,
            "DriverLambda",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path=os.path.join(os.path.dirname(__file__), "../lambda/driver"),
                exclude=["*.pyc", "__pycache__"],
            ),
            role=lambda_role,
            environment={
                "BUCKET": self.bucket.bucket_name,
            },
            timeout=Duration.seconds(120),
        )

        # Driver can invoke plotting
        self.plotting_lambda.grant_invoke(self.driver_lambda)

        # ====== OUTPUTS ======

        CfnOutput(
            self,
            "PlottingLambdaArn",
            value=self.plotting_lambda.function_arn,
            export_name="PlottingLambdaArn",
        )

        CfnOutput(
            self,
            "BucketName",
            value=self.bucket.bucket_name,
        )

        CfnOutput(
            self,
            "TableName",
            value=self.table.table_name,
        )

        CfnOutput(
            self,
            "DriverLambdaName",
            value=self.driver_lambda.function_name,
        )

        CfnOutput(
            self,
            "SizeTrackingLambdaName",
            value=self.size_tracking_lambda.function_name,
        )

    def _get_matplotlib_layer(self):
        """Get matplotlib layer from Assignment 2."""
        matplotlib_layer_arn = f"arn:aws:lambda:{self.region}:{self.account}:layer:matplotlib-layer:1"
        try:
            return lambda_.LayerVersion.from_layer_version_arn(
                self, "MatplotlibLayer", matplotlib_layer_arn
            )
        except Exception:
            return None
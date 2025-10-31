from aws_cdk import (
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_iam as iam,
    Stack,
    Duration,
)
from constructs import Construct
import os


class LambdaStack(Stack):
    """Lambda stack containing Plotting Lambda, Driver Lambda, and REST API"""

    def __init__(self, scope: Construct, id: str, bucket: s3.Bucket, table: dynamodb.Table, **kwargs):
        super().__init__(scope, id, **kwargs)

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

        # ====== PLOTTING LAMBDA ======
        plotting_layers = []
        try:
            matplotlib_layer = self._get_matplotlib_layer()
            if matplotlib_layer:
                plotting_layers.append(matplotlib_layer)
        except Exception:
            pass

        plotting_lambda = lambda_.Function(
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
                "DDB_TABLE": table.table_name,
                "BUCKET": bucket.bucket_name,
                "GSI_NAME": "bucket_size_index",
            },
            timeout=Duration.seconds(60),
            layers=plotting_layers if plotting_layers else None,
            memory_size=512,
        )

        # Grant S3 write access
        bucket.grant_write(plotting_lambda)

        # Grant DynamoDB read access
        table.grant_read_data(plotting_lambda)

        # ====== REST API ======
        api = apigw.RestApi(
            self,
            "PlottingAPI",
            rest_api_name="S3-Monitoring-Plotting-API",
            description="API to trigger S3 bucket size plotting",
        )

        # Add GET method
        api.root.add_method(
            "GET",
            apigw.LambdaIntegration(plotting_lambda),
        )

        # ====== DRIVER LAMBDA ======
        driver_lambda = lambda_.Function(
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
                "BUCKET": bucket.bucket_name,
                "PLOTTING_API": api.url,  # Pass API URL directly
            },
            timeout=Duration.seconds(120),
        )

        # Grant S3 write access
        bucket.grant_write(driver_lambda)

    def _get_matplotlib_layer(self):
        """Get matplotlib layer from Assignment 2."""
        matplotlib_layer_arn = f"arn:aws:lambda:{self.region}:{self.account}:layer:matplotlib-layer:1"
        try:
            return lambda_.LayerVersion.from_layer_version_arn(
                self, "MatplotlibLayer", matplotlib_layer_arn
            )
        except Exception:
            return None
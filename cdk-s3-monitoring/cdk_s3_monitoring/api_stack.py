from aws_cdk import (
    aws_apigateway as apigw,
    aws_lambda as lambda_,
    Stack,
    CfnOutput,
    Fn,
)
from constructs import Construct


class ApiStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        plotting_lambda_arn_export_name: str = "PlottingLambdaArn",
        **kwargs
    ):
        super().__init__(scope, id, **kwargs)

        plotting_lambda_arn = Fn.import_value(plotting_lambda_arn_export_name)

        plotting_lambda = lambda_.Function.from_function_arn(
            self,
            "ImportedPlottingLambda",
            plotting_lambda_arn,
        )

        api = apigw.RestApi(
            self,
            "PlottingAPI",
            rest_api_name="S3-Monitoring-Plotting-API",
            description="API to trigger S3 bucket size plotting",
        )

        plot_resource = api.root.add_resource("plot")

        plot_resource.add_method(
            "GET",
            apigw.LambdaIntegration(plotting_lambda),
        )

        CfnOutput(
            self,
            "PlottingAPIEndpoint",
            value=api.url_for_path("/plot"),
        )
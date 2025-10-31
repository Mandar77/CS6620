from aws_cdk import App
from cdk_s3_monitoring.compute_stack import ComputeStack
from cdk_s3_monitoring.api_stack import ApiStack

app = App()

compute = ComputeStack(app, "ComputeStack")
api = ApiStack(app, "ApiStack")

app.synth()

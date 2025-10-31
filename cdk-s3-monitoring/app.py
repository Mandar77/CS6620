from aws_cdk import App
from cdk_s3_monitoring.storage_stack import StorageStack
from cdk_s3_monitoring.lambda_stack import LambdaStack

app = App()

# First create storage stack
storage = StorageStack(app, "StorageStack")

# Then create lambda stack, passing storage resources as props
lambdas = LambdaStack(
    app,
    "LambdaStack",
    bucket=storage.bucket,
    table=storage.table,
)

app.synth()

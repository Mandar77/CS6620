from aws_cdk import (
    aws_s3 as s3,
    aws_s3_notifications as s3_notifications,
    aws_lambda as lambda_,
    Stack,
    Fn,
)
from constructs import Construct


class EventStack(Stack):
    """
    This stack adds S3 event notifications to the bucket created in ComputeStack.
    Deploy AFTER ComputeStack to avoid circular dependencies.
    """
    
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Import the bucket name from ComputeStack outputs
        bucket_name = Fn.import_value("ComputeStackBucketName")
        bucket = s3.Bucket.from_bucket_name(self, "ImportedBucket", bucket_name)

        # Import the size tracking lambda ARN from ComputeStack outputs
        lambda_arn = Fn.import_value("SizeTrackingLambdaArn")
        size_tracking_lambda = lambda_.Function.from_function_arn(
            self, "ImportedSizeTrackingLambda", lambda_arn
        )

        # Add S3 event notifications
        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(size_tracking_lambda),
        )

        bucket.add_event_notification(
            s3.EventType.OBJECT_REMOVED,
            s3_notifications.LambdaDestination(size_tracking_lambda),
        )
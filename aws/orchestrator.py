import boto3
import os
import time

sm = boto3.client("sagemaker")

def lambda_handler(event, context):
    role = os.environ["SAGEMAKER_ROLE"]
    image = os.environ["IMAGE_URI"]
    bucket = os.environ["BUCKET_NAME"]

    job_name = f"filme-job-{int(time.time())}"

    response = sm.create_processing_job(
        ProcessingJobName=job_name,
        RoleArn=role,
        ProcessingResources={
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": "ml.m5.large",
                "VolumeSizeInGB": 30,
            }
        },
        AppSpecification={
            "ImageUri": image,
            "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/handler.py"]
        },
        ProcessingInputs=[],
        ProcessingOutputConfig={
            "Outputs": [
                {
                    "OutputName": "filmes-output",
                    "S3Output": {
                        "S3Uri": f"s3://{bucket}/output/",
                        "LocalPath": "/opt/ml/processing/output",
                        "S3UploadMode": "EndOfJob",
                    }
                }
            ]
        },
    )

    return {"status": "STARTED", "job_name": job_name}

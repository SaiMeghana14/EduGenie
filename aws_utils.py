# aws_utils.py
import os
import json
import boto3
from botocore.exceptions import ClientError
from typing import Optional, Dict, Any

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
USE_AWS = os.getenv("USE_AWS", "false").lower() == "true"

def get_boto_client(service_name: str):
    if not USE_AWS:
        raise RuntimeError("AWS usage disabled. Set USE_AWS=true and configure AWS credentials to enable.")
    return boto3.client(service_name, region_name=AWS_REGION)

# DynamoDB helpers (progress)
def init_progress_table(table_name: str):
    if not USE_AWS:
        return
    client = get_boto_client("dynamodb")
    try:
        client.describe_table(TableName=table_name)
        return
    except client.exceptions.ResourceNotFoundException:
        # create
        client.create_table(
            TableName=table_name,
            KeySchema=[{"AttributeName":"user_id","KeyType":"HASH"}],
            AttributeDefinitions=[{"AttributeName":"user_id","AttributeType":"S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        waiter = client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

def save_progress_dynamodb(table_name: str, user_id: str, progress: Dict[str, Any]):
    if not USE_AWS:
        raise RuntimeError("AWS disabled.")
    client = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = client.Table(table_name)
    table.put_item(Item={"user_id": user_id, "progress": progress})

def load_progress_dynamodb(table_name: str, user_id: str) -> Optional[Dict[str,Any]]:
    if not USE_AWS:
        return None
    client = boto3.resource('dynamodb', region_name=AWS_REGION)
    table = client.Table(table_name)
    resp = table.get_item(Key={"user_id": user_id})
    return resp.get("Item", {}).get("progress")

# S3 helpers for lessons/content
def upload_lesson_to_s3(bucket: str, key: str, content: str):
    if not USE_AWS:
        raise RuntimeError("AWS disabled.")
    client = get_boto_client("s3")
    client.put_object(Bucket=bucket, Key=key, Body=content)

def download_lesson_from_s3(bucket: str, key: str) -> Optional[str]:
    if not USE_AWS:
        return None
    client = get_boto_client("s3")
    try:
        resp = client.get_object(Bucket=bucket, Key=key)
        return resp["Body"].read().decode("utf-8")
    except ClientError:
        return None

# Polly voice (optional)
def text_to_speech_polly(text: str, voice: str="Aditi", output_format: str="mp3") -> bytes:
    if not USE_AWS:
        raise RuntimeError("AWS disabled.")
    polly = get_boto_client("polly")
    resp = polly.synthesize_speech(Text=text, OutputFormat=output_format, VoiceId=voice)
    return resp["AudioStream"].read()

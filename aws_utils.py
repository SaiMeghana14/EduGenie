import os
import boto3
from botocore.exceptions import NoRegionError, NoCredentialsError, ClientError
import streamlit as st

# --------------------------------------------------------
# ⚙️ AWS Configuration
# --------------------------------------------------------
DEFAULT_REGION = "us-east-1"  # change to "ap-south-1" for India
USE_AWS = True  # Toggle this if running locally without AWS access

def get_region():
    """Return configured AWS region."""
    return os.getenv("AWS_DEFAULT_REGION", DEFAULT_REGION)

def get_client(service):
    """Safely return boto3 client with proper region handling."""
    try:
        return boto3.client(service, region_name=get_region())
    except NoRegionError:
        st.error("❌ AWS region not configured. Defaulting to us-east-1.")
        return boto3.client(service, region_name="us-east-1")
    except NoCredentialsError:
        st.warning("⚠️ AWS credentials not found. Using mock mode.")
        return None

def get_resource(service):
    """Safely return boto3 resource with region fallback."""
    try:
        return boto3.resource(service, region_name=get_region())
    except NoRegionError:
        return boto3.resource(service, region_name="us-east-1")

# --------------------------------------------------------
# 🤖 AWS Clients
# --------------------------------------------------------
translate = get_client("translate")
dynamodb = get_resource("dynamodb")
bedrock = get_client("bedrock-runtime")

# --------------------------------------------------------
# 📊 DynamoDB Utilities for Progress Tracking
# --------------------------------------------------------
TABLE_NAME = "EduGenieProgress"

def init_progress_table():
    """Create the DynamoDB table if not exists."""
    if not USE_AWS or dynamodb is None:
        return
    try:
        existing = list(dynamodb.tables.all())
        if any(t.name == TABLE_NAME for t in existing):
            return  # Table exists
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "student_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "student_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
    except ClientError as e:
        if "ResourceInUseException" not in str(e):
            st.error(f"Error creating table: {e}")

def save_progress_dynamodb(student_id, progress_data):
    """Save student progress."""
    if not USE_AWS or dynamodb is None:
        return
    try:
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(Item={"student_id": student_id, **progress_data})
    except Exception as e:
        st.warning(f"⚠️ Could not save progress: {e}")

def load_progress_dynamodb(student_id):
    """Load student progress."""
    if not USE_AWS or dynamodb is None:
        return {}
    try:
        table = dynamodb.Table(TABLE_NAME)
        resp = table.get_item(Key={"student_id": student_id})
        return resp.get("Item", {})
    except Exception as e:
        st.warning(f"⚠️ Could not load progress: {e}")
        return {}

# --------------------------------------------------------
# 🌍 Translation & Voice (AWS Translate + Polly)
# --------------------------------------------------------
def translate_text(text, target_lang="hi"):
    """Translate content using AWS Translate."""
    if not translate:
        return text
    try:
        result = translate.translate_text(Text=text, SourceLanguageCode="en", TargetLanguageCode=target_lang)
        return result.get("TranslatedText", text)
    except Exception as e:
        st.warning(f"⚠️ Translation failed: {e}")
        return text

def synthesize_speech(text, voice="Joanna"):
    """Generate speech from text using AWS Polly."""
    try:
        polly = boto3.client("polly", region_name=get_region())
        response = polly.synthesize_speech(Text=text, VoiceId=voice, OutputFormat="mp3")
        return response["AudioStream"].read()
    except Exception as e:
        st.warning(f"⚠️ Polly speech generation failed: {e}")
        return None

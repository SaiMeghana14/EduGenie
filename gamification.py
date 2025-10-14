import os
import boto3
import uuid
from botocore.exceptions import NoRegionError, ClientError

# Get region safely
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")  # default fallback region

try:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table_name = os.getenv("DDB_TABLE_NAME", "EduGenieScores")
    table = dynamodb.Table(table_name)
except NoRegionError:
    print("⚠️ No AWS region found. Using fallback (mock leaderboard).")
    dynamodb = None
    table = None


def update_score(user_id, points):
    if table is None:
        print("⚠️ DynamoDB not configured. Skipping score update.")
        return

    try:
        table.update_item(
            Key={"UserId": user_id},
            UpdateExpression="SET points = if_not_exists(points, :start) + :inc",
            ExpressionAttributeValues={":inc": points, ":start": 0}
        )
    except ClientError as e:
        print(f"❌ Error updating DynamoDB: {e}")


def get_leaderboard(limit=10):
    if table is None:
        print("⚠️ DynamoDB not connected. Returning demo leaderboard.")
        return [
            {"UserId": "Alice", "points": 120},
            {"UserId": "Bob", "points": 100},
            {"UserId": "Charlie", "points": 80},
        ]

    try:
        response = table.scan()
        players = sorted(response.get("Items", []), key=lambda x: x.get("points", 0), reverse=True)
        return players[:limit]
    except ClientError as e:
        print(f"❌ Error fetching leaderboard: {e}")
        return []


def award_badge(user_id, badge_name):
    if table is None:
        print("⚠️ DynamoDB not configured. Skipping badge award.")
        return

    try:
        badge_id = str(uuid.uuid4())
        table.update_item(
            Key={"UserId": user_id},
            UpdateExpression="ADD badges :b",
            ExpressionAttributeValues={":b": {badge_name}}
        )
    except ClientError as e:
        print(f"❌ Error awarding badge: {e}")

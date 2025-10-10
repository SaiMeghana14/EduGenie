import boto3
import uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("EduGenieScores")

def update_score(user_id, points):
    table.update_item(
        Key={"UserId": user_id},
        UpdateExpression="SET points = if_not_exists(points, :start) + :inc",
        ExpressionAttributeValues={":inc": points, ":start": 0}
    )

def get_leaderboard(limit=10):
    response = table.scan()
    players = sorted(response["Items"], key=lambda x: x.get("points", 0), reverse=True)
    return players[:limit]

def award_badge(user_id, badge_name):
    badge_id = str(uuid.uuid4())
    table.update_item(
        Key={"UserId": user_id},
        UpdateExpression="ADD badges :b",
        ExpressionAttributeValues={":b": {badge_name}}
    )

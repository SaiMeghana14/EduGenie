import os, time, json
from typing import List, Dict, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_BOTO3 = True
except Exception:
    HAS_BOTO3 = False

class DBAWS:
    """
    DynamoDB-based persistence layer. Assumes these DynamoDB tables exist:
      - EduGenieUsers (PK: user)
      - EduGenieQuizHistory (PK: user, SK: ts)
      - EduGeniePlans (PK: user)
    You can create them manually in the AWS Console or with CloudFormation.
    """

    def __init__(self, region_name="us-east-1",
                 users_table="EduGenieUsers",
                 quiz_table="EduGenieQuizHistory",
                 plans_table="EduGeniePlans",
                 s3_bucket: Optional[str] = None):
        self.region = region_name
        self.users_table = users_table
        self.quiz_table = quiz_table
        self.plans_table = plans_table
        self.s3_bucket = s3_bucket
        self.dynamo = None
        self.s3 = None
        if HAS_BOTO3:
            self.dynamo = boto3.resource("dynamodb", region_name=self.region)
            self.s3 = boto3.client("s3", region_name=self.region)
            # get table references (may raise if missing)
            self._users = self.dynamo.Table(self.users_table)
            self._quiz = self.dynamo.Table(self.quiz_table)
            self._plans = self.dynamo.Table(self.plans_table)

    # User XP
    def add_xp(self, user: str, xp: int):
        if not self.dynamo:
            return
        # upsert with increment
        try:
            self._users.update_item(
                Key={"user": user},
                UpdateExpression="ADD xp :inc SET last_active = :ts",
                ExpressionAttributeValues={":inc": xp, ":ts": int(time.time())},
                ReturnValues="UPDATED_NEW"
            )
        except ClientError as e:
            print("DynamoDB add_xp error:", e)

    def get_xp(self, user: str) -> int:
        if not self.dynamo:
            return 0
        try:
            r = self._users.get_item(Key={"user": user})
            item = r.get("Item", {})
            return int(item.get("xp", 0))
        except Exception:
            return 0

    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Simple scan and sort. For production, design GSI for sorted queries.
        """
        if not self.dynamo:
            return []
        try:
            resp = self._users.scan()
            items = resp.get("Items", [])
            items_sorted = sorted(items, key=lambda it: int(it.get("xp", 0)), reverse=True)
            return items_sorted[:limit]
        except Exception as e:
            print("DynamoDB leaderboard error:", e)
            return []

    # Quiz history
    def save_quiz_result(self, user: str, topic: str, score: int, total: int):
        if not self.dynamo:
            return
        ts = int(time.time())
        try:
            self._quiz.put_item(Item={
                "user": user,
                "ts": ts,
                "topic": topic,
                "score": int(score),
                "total": int(total)
            })
        except Exception as e:
            print("DynamoDB save_quiz_result:", e)

    def get_recent_quiz_scores(self, user: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.dynamo:
            return []
        try:
            # Query by user; requires a GSI or design where user is partition key (we used user as PK)
            resp = self._quiz.query(KeyConditionExpression=boto3.dynamodb.conditions.Key('user').eq(user),
                                    ScanIndexForward=False, Limit=limit)
            return resp.get("Items", [])
        except Exception:
            # fallback to scan + filter (less efficient)
            resp = self._quiz.scan()
            items = [it for it in resp.get("Items", []) if it.get("user") == user]
            items_sorted = sorted(items, key=lambda it: it.get("ts", 0), reverse=True)
            return items_sorted[:limit]

    # Learning plans
    def save_learning_plan(self, user: str, plan_obj: Dict[str, Any]):
        if not self.dynamo:
            return
        try:
            self._plans.put_item(Item={
                "user": user,
                "plan": json.dumps(plan_obj),
                "updated_at": int(time.time())
            })
        except Exception as e:
            print("DynamoDB save_learning_plan:", e)

    def get_learning_plan(self, user: str) -> Optional[Dict[str, Any]]:
        if not self.dynamo:
            return None
        try:
            r = self._plans.get_item(Key={"user": user})
            item = r.get("Item")
            if not item:
                return None
            return json.loads(item.get("plan", "{}"))
        except Exception:
            return None

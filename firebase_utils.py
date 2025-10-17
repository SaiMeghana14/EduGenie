import os, json, time
import firebase_admin
from firebase_admin import credentials, db
from typing import Optional

def init_firebase():
    # read service account JSON from secrets (string)
    svc_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    db_url = os.environ.get("FIREBASE_DB_URL")
    if not svc_json or not db_url:
        raise RuntimeError("Firebase service account or DB URL not set in env")
    # ensure single init
    if not firebase_admin._apps:
        cred = credentials.Certificate(json.loads(svc_json))
        firebase_admin.initialize_app(cred, {'databaseURL': db_url})
    return True

def push_session(user: str, payload: dict):
    init_firebase()
    ref = db.reference(f"/sessions/{user}")
    key = ref.push(payload)
    return key.key

def save_room_metadata(room_id: str, payload: dict):
    init_firebase()
    ref = db.reference(f"/rooms/{room_id}")
    ref.update(payload)

def get_room_metadata(room_id: str) -> Optional[dict]:
    init_firebase()
    ref = db.reference(f"/rooms/{room_id}")
    return ref.get()

def push_chat_message(room_id: str, user: str, message: str):
    init_firebase()
    ref = db.reference(f"/messages/{room_id}")
    payload = {'user': user, 'message': message, 'ts': int(time.time())}
    return ref.push(payload).key

def get_leaderboard(limit=10):
    init_firebase()
    ref = db.reference('/leaderboard')
    data = ref.order_by_child('xp').limit_to_last(limit).get()
    # transform to list
    res = []
    if data:
        for k,v in data.items():
            res.append({'name': v.get('name'), 'xp': v.get('xp',0)})
    res.sort(key=lambda x: x['xp'], reverse=True)
    return res

def update_leaderboard(name: str, xp: int):
    init_firebase()
    ref = db.reference('/leaderboard')
    # set or update
    # simple set by name key
    ref.child(name).set({'name': name, 'xp': xp})
    return True

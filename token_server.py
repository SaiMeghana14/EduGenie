# token_server.py
from flask import Flask, request, jsonify
import threading, os, jwt, time
from firebase_utils import get_room_metadata

app = Flask(__name__)
JWT_SECRET = os.environ.get("JWT_SECRET") or os.environ.get("JWT_SECRET_KEY")

@app.route('/validate_token', methods=['POST'])
def validate_token():
    data = request.json or {}
    token = data.get('token')
    room = data.get('room')
    if not token or not room:
        return jsonify({'ok': False, 'error': 'missing token or room'}), 400
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        # optional: check payload room matches
        if payload.get('room') != room:
            return jsonify({'ok': False, 'error': 'token room mismatch'}), 403
        # cross-check with firebase room metadata if you want extra validation
        meta = get_room_metadata(room)
        # e.g., meta may contain allowed_issued_at or token_id
        return jsonify({'ok': True, 'payload': payload})
    except jwt.ExpiredSignatureError:
        return jsonify({'ok': False, 'error': 'expired'}), 403
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 403

def run_server(port=5001):
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def start_in_background(port=5001):
    t = threading.Thread(target=run_server, kwargs={'port':port}, daemon=True)
    t.start()
    return t

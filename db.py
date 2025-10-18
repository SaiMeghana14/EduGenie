import sqlite3
import os
import pandas as pd
from typing import List, Dict, Any
import time

class DB:
    def __init__(self, path="edugenie.db"):
        self.path = path
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._ensure_tables()

    def _ensure_tables(self):
        cur = self._conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            profile JSON
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT,
            ts INTEGER
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            ts INTEGER
        )""")
        self._conn.commit()

    # XP / leaderboard
    def add_xp(self, user: str, xp: int):
        cur = self._conn.cursor()
        cur.execute("INSERT OR IGNORE INTO users (user, xp) VALUES (?, 0)", (user,))
        cur.execute("UPDATE users SET xp = xp + ? WHERE user = ?", (xp, user))
        self._conn.commit()

    def get_xp(self, user: str) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT xp FROM users WHERE user = ?", (user,))
        r = cur.fetchone()
        return int(r[0]) if r else 0

    def get_leaderboard(self, limit=10) -> List[Dict[str,Any]]:
        cur = self._conn.cursor()
        cur.execute("SELECT user, xp FROM users ORDER BY xp DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        return [{"user": r[0], "xp": r[1]} for r in rows]

    # cache
    def cache_set(self, key: str, value: str, ts: int=None):
        ts = ts or int(time.time())
        cur = self._conn.cursor()
        cur.execute("INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)", (key, value, ts))
        self._conn.commit()

    def cache_get(self, key: str):
        cur = self._conn.cursor()
        cur.execute("SELECT value FROM cache WHERE key = ?", (key,))
        r = cur.fetchone()
        return r[0] if r else None

    # quiz history
    def add_quiz_result(self, user: str, topic: str, score: int, total: int):
        cur = self._conn.cursor()
        cur.execute("INSERT INTO quiz_history (user, topic, score, total, ts) VALUES (?, ?, ?, ?, ?)",
                    (user, topic, score, total, int(time.time())))
        self._conn.commit()

    def get_recent_quiz_scores(self, user: str, limit: int=5):
        cur = self._conn.cursor()
        cur.execute("SELECT topic, score, total, ts FROM quiz_history WHERE user = ? ORDER BY ts DESC LIMIT ?", (user, limit))
        rows = cur.fetchall()
        return [{"topic": r[0], "score": r[1], "total": r[2], "ts": r[3]} for r in rows]

    def get_all_quiz_history(self, user: str):
        cur = self._conn.cursor()
        cur.execute("SELECT topic, score, total, ts FROM quiz_history WHERE user = ?", (user,))
        rows = cur.fetchall()
        return [{"topic": r[0], "score": r[1], "total": r[2], "ts": r[3]} for r in rows]

    def get_activity_dataframe(self):
        cur = self._conn.cursor()
        cur.execute("SELECT user, topic, score, total, ts FROM quiz_history")
        rows = cur.fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows, columns=["user","topic","score","total","ts"])
        df['ts'] = pd.to_datetime(df['ts'], unit='s')
        return df

    def reset_db(self):
        cur = self._conn.cursor()
        cur.execute("DROP TABLE IF EXISTS users")
        cur.execute("DROP TABLE IF EXISTS cache")
        cur.execute("DROP TABLE IF EXISTS quiz_history")
        self._conn.commit()
        self._ensure_tables()

    def get_leaderboard(self, limit=10):
        return self.get_leaderboard(limit)

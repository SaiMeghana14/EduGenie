import sqlite3
import os
from typing import Optional

class DB:
    def __init__(self, db_path='edugenie.db'):
        need_init = not os.path.exists(db_path)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        if need_init:
            self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        c.execute('CREATE TABLE users(name TEXT PRIMARY KEY, xp INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE cache(key TEXT PRIMARY KEY, value TEXT, timestamp INTEGER)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_cache_key ON cache(key)')
        self.conn.commit()

    # XP operations
    def add_xp(self, name: str, xp: int):
        c = self.conn.cursor()
        r = c.execute('SELECT xp FROM users WHERE name=?', (name,)).fetchone()
        if r:
            c.execute('UPDATE users SET xp=? WHERE name=?', (r[0]+xp, name))
        else:
            c.execute('INSERT INTO users(name, xp) VALUES(?, ?)', (name, xp))
        self.conn.commit()

    def get_xp(self, name: str) -> int:
        r = self.conn.cursor().execute('SELECT xp FROM users WHERE name=?', (name,)).fetchone()
        return r[0] if r else 0

    def get_leaderboard(self, limit=10):
        rows = list(self.conn.cursor().execute('SELECT name, xp FROM users ORDER BY xp DESC LIMIT ?', (limit,)).fetchall())
        return [{'name': r[0], 'xp': r[1]} for r in rows]

    def reset_db(self):
        c = self.conn.cursor()
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('DROP TABLE IF EXISTS cache')
        self.conn.commit()
        self._init_db()

    # simple cache operations for offline / rate limiting
    def cache_set(self, key: str, value: str, timestamp: int):
        c = self.conn.cursor()
        c.execute('REPLACE INTO cache(key, value, timestamp) VALUES(?,?,?)', (key, value, timestamp))
        self.conn.commit()

    def cache_get(self, key: str) -> Optional[str]:
        r = self.conn.cursor().execute('SELECT value FROM cache WHERE key=?', (key,)).fetchone()
        return r[0] if r else None

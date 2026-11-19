import hashlib
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path


def empty_profile():
    return {"drafts": {}, "attempts": {}, "mock": None}


class Store:
    def __init__(self, token):
        self.key = hashlib.sha256(token.encode()).hexdigest()
        self.path = Path(os.environ.get("DCO_DB_PATH", Path(__file__).parent / "data" / "practice.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL, payload TEXT NOT NULL
            )""")

    def load(self):
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT revision, payload FROM profiles WHERE id = ?", (self.key,)).fetchone()
        return (row[0], json.loads(row[1])) if row else (0, empty_profile())

    def save(self, revision, profile):
        payload = json.dumps(profile, ensure_ascii=False)
        with closing(sqlite3.connect(self.path)) as db, db:
            cursor = db.execute("""
                INSERT INTO profiles VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET revision = excluded.revision, payload = excluded.payload
                WHERE profiles.revision = ?
            """, (self.key, revision + 1, payload, revision))
            if cursor.rowcount != 1:
                raise sqlite3.OperationalError("profile updated in another tab")
        return revision + 1

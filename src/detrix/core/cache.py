"""SHA256 content-addressable step cache.

Memoizes step outputs by hashing step_id + input data.
If inputs haven't changed, the step is skipped and cached output returned.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def _stable_hash(data: Any) -> str:
    """SHA256 hash of JSON-serialized data with sorted keys."""
    raw = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def hash_file(path: str) -> str:
    """SHA256 of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class StepCache:
    """SQLite-backed content-addressable cache for step outputs."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS step_cache (
                    cache_key   TEXT PRIMARY KEY,
                    step_id     TEXT NOT NULL,
                    input_hash  TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

    def make_key(self, step_id: str, inputs: dict[str, Any]) -> str:
        """Cache key = SHA256(step_id + sorted input hash)."""
        input_hash = _stable_hash(inputs)
        combined = f"{step_id}:{input_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, step_id: str, inputs: dict[str, Any]) -> dict[str, Any] | None:
        """Return cached output if inputs match, else None."""
        key = self.make_key(step_id, inputs)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT output_json FROM step_cache WHERE cache_key = ?", (key,)
            ).fetchone()
        if row:
            loaded = json.loads(row[0])
            return loaded if isinstance(loaded, dict) else {"result": loaded}
        return None

    def put(
        self, step_id: str, inputs: dict[str, Any], output: dict[str, Any]
    ) -> str:
        """Store step output. Returns cache key."""
        key = self.make_key(step_id, inputs)
        input_hash = _stable_hash(inputs)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO step_cache
                   (cache_key, step_id, input_hash, output_json)
                   VALUES (?, ?, ?, ?)""",
                (key, step_id, input_hash, json.dumps(output, default=str)),
            )
        return key

    def invalidate(self, step_id: str | None = None) -> int:
        """Clear cache entries. If step_id given, only that step."""
        with sqlite3.connect(self.db_path) as conn:
            if step_id:
                cur = conn.execute(
                    "DELETE FROM step_cache WHERE step_id = ?", (step_id,)
                )
            else:
                cur = conn.execute("DELETE FROM step_cache")
            return cur.rowcount

    def input_hash(self, inputs: dict[str, Any]) -> str:
        return _stable_hash(inputs)

    def output_hash(self, output: dict[str, Any]) -> str:
        return _stable_hash(output)

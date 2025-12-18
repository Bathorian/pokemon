from __future__ import annotations

from typing import Any, Optional
import os
import sqlite3
import json

# Database lives next to the root app.py by default
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "pokeapi_calls.sqlite3")


def db_init() -> None:
    """Ensure SQLite database and table exist. Best-effort."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_calls (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts_utc TEXT NOT NULL,
                  identifier TEXT,
                  url TEXT NOT NULL,
                  status INTEGER,
                  duration_ms REAL,
                  payload_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_ts ON api_calls(ts_utc)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_api_calls_endpoint ON api_calls(endpoint)")
    except Exception:
        # Logging must never break the API
        pass


def save_api_call(ts_utc: str, endpoint: Optional[str], identifier: Optional[str], url: str,
                  status: Optional[int], duration_ms: Optional[float], payload: Any) -> None:
    """Persist a single API call record. Best-effort, failures are swallowed."""
    if endpoint != "pokemon":
        return

    try:
        payload_text = None
        try:
            payload_text = json.dumps(payload, ensure_ascii=False)
        except Exception:
            payload_text = None
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO api_calls (ts_utc, endpoint , identifier, url, status, duration_ms, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts_utc, endpoint, identifier, url, status, duration_ms, payload_text),
            )
    except Exception:
        # Avoid blowing up API on logging issues
        pass

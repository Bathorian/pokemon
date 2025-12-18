from __future__ import annotations

import time


def now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 basic format (Z suffix)."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

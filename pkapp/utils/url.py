from __future__ import annotations

from typing import Optional, Tuple
import re


def split_endpoint_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of endpoint and identifier from a full PokeAPI URL.

    Example: https://pokeapi.co/api/v2/pokemon/25/ -> ("pokemon", "25")
    """
    try:
        rest = url.split("/api/v2/")[-1]
        parts = [p for p in rest.split("/") if p]
        if not parts:
            return None, None
        endpoint = parts[0]
        identifier = parts[1] if len(parts) > 1 else None
        return endpoint, identifier
    except Exception:
        return None, None


def extract_id_from_url(url: str) -> Optional[int]:
    """Extract numeric ID suffix from a PokeAPI URL; return None if not found."""
    if not isinstance(url, str):
        return None
    m = re.search(r"/(\d+)/?$", url)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None

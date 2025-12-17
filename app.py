from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import requests
import sqlite3
import json
import time
import flask
from flask import Flask, jsonify, send_file, Response
from flask_cors import CORS

from main import summarize_pokemon, POKEAPI_BASE

app = Flask(__name__, static_folder=None)
CORS(app)

# ==================== CONSTANTS ====================

BASE_URL = "https://pokeapi.co/api/v2"
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites"
SPRITE_EXT = "png"

ENDPOINTS = [
    "ability",
    "berry",
    "berry-firmness",
    "berry-flavor",
    "characteristic",
    "contest-effect",
    "contest-type",
    "egg-group",
    "encounter-condition",
    "encounter-condition-value",
    "encounter-method",
    "evolution-chain",
    "evolution-trigger",
    "gender",
    "generation",
    "growth-rate",
    "item",
    "item-attribute",
    "item-category",
    "item-fling-effect",
    "item-pocket",
    "language",
    "location",
    "location-area",
    "machine",
    "move",
    "move-ailment",
    "move-battle-style",
    "move-category",
    "move-damage-class",
    "move-learn-method",
    "move-target",
    "nature",
    "pal-park-area",
    "pokeathlon-stat",
    "pokedex",
    "pokemon",
    "pokemon-color",
    "pokemon-form",
    "pokemon-habitat",
    "pokemon-shape",
    "pokemon-species",
    "region",
    "stat",
    "super-contest-effect",
    "type",
    "version",
    "version-group",
]


def validate_endpoint(endpoint: str, resource_id: Optional[str] = None) -> None:
    """Validate that the endpoint exists in the API."""
    if endpoint not in ENDPOINTS:
        raise ValueError(f"Unknown API endpoint '{endpoint}'")
    if resource_id is not None and not isinstance(resource_id, (int, str)):
        raise ValueError(f"Bad resource_id '{resource_id}'")


def api_url_build(endpoint: str, resource_id: Optional[str] = None, subresource: Optional[str] = None) -> str:
    """Build a complete PokeAPI URL."""
    validate_endpoint(endpoint, resource_id)

    parts = [BASE_URL, endpoint]
    if resource_id is not None:
        parts.append(str(resource_id))
    if subresource is not None:
        parts.append(subresource)

    return "/".join(parts) + ("/" if resource_id or subresource else "")


def sprite_url_build(sprite_type: str, sprite_id: int, **kwargs) -> str:
    """Build a sprite URL with various options."""
    options = parse_sprite_options(sprite_type, **kwargs)
    filename = f"{sprite_id}.{SPRITE_EXT}"
    url = "/".join([SPRITE_URL, sprite_type, *options, filename])
    return url


def sprite_filepath_build(sprite_type: str, sprite_id: int, **kwargs) -> str:
    """Build a sprite filepath (relative to sprite cache)."""
    options = parse_sprite_options(sprite_type, **kwargs)
    filename = f"{sprite_id}.{SPRITE_EXT}"
    filepath = os.path.join(sprite_type, *options, filename)
    return filepath


def parse_sprite_options(sprite_type: str, **kwargs) -> List[str]:
    """Parse sprite options based on type and kwargs."""
    options = []

    if sprite_type == "pokemon":
        if kwargs.get("model", False):
            options.append("model")
        elif kwargs.get("other", False):
            options.append("other")
            if kwargs.get("official_artwork", False):
                options.append("official-artwork")
            if kwargs.get("dream_world", False):
                options.append("dream-world")
        else:
            if kwargs.get("back", False):
                options.append("back")
            if kwargs.get("shiny", False):
                options.append("shiny")
            if kwargs.get("female", False):
                options.append("female")

    elif sprite_type == "items":
        if kwargs.get("berries", False):
            options.append("berries")
        elif kwargs.get("dream_world", False):
            options.append("dream-world")
        elif kwargs.get("gen3", False):
            options.append("gen3")
        elif kwargs.get("gen5", False):
            options.append("gen5")
        elif kwargs.get("underground", False):
            options.append("underground")

    return options


# ==================== HELPER FUNCTIONS ====================

# ---- SQLite logging ----

DB_PATH = os.path.join(os.path.dirname(__file__), "pokeapi_calls.sqlite3")


def _db_init() -> None:
    """Ensure SQLite database and table exist."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_calls (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts_utc TEXT NOT NULL,
                  endpoint TEXT,
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


def _save_api_call(ts_utc: str, endpoint: Optional[str], identifier: Optional[str], url: str,
                   status: Optional[int], duration_ms: Optional[float], payload: Any) -> None:
    """Persist a single API call record. Best-effort, failures are swallowed."""
    try:
        payload_text = None
        try:
            payload_text = json.dumps(payload, ensure_ascii=False)
        except Exception:
            payload_text = None
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO api_calls (ts_utc, endpoint, identifier, url, status, duration_ms, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts_utc, endpoint, identifier, url, status, duration_ms, payload_text),
            )
    except Exception:
        # Avoid blowing up API on logging issues
        pass


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _split_endpoint_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of endpoint and identifier from a full PokeAPI URL."""
    try:
        # Expecting .../api/v2/<endpoint>/<identifier>/...
        rest = url.split("/api/v2/")[-1]
        parts = [p for p in rest.split("/") if p]
        if not parts:
            return None, None
        endpoint = parts[0]
        identifier = parts[1] if len(parts) > 1 else None
        return endpoint, identifier
    except Exception:
        return None, None

def _http_get_json(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Helper to fetch JSON from a URL (with SQLite logging)."""
    t0 = time.perf_counter()
    r = requests.get(url, timeout=timeout)
    dur = (time.perf_counter() - t0) * 1000.0
    payload: Any
    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
    ep, ident = _split_endpoint_from_url(url)
    _save_api_call(_now_iso(), ep, ident, url, r.status_code, dur, payload)
    r.raise_for_status()
    # If non-JSON earlier, raise_for_status would have raised. Ensure dict on return
    return payload if isinstance(payload, dict) else payload  # type: ignore[return-value]


def _proxy_endpoint(endpoint: str, identifier: Optional[str] = None, timeout: float = 10.0) -> tuple[
    Dict[str, Any], int]:
    """
    Generic proxy to PokeAPI endpoints.
    If identifier is None, returns a paginated list.
    Otherwise, returns the specific resource.
    """
    try:
        validate_endpoint(endpoint, identifier)
        url = api_url_build(endpoint, identifier)

        t0 = time.perf_counter()
        r = requests.get(url, timeout=timeout)
        dur = (time.perf_counter() - t0) * 1000.0
        try:
            payload = r.json()
        except Exception:
            payload = {"error": r.text}
        _save_api_call(_now_iso(), endpoint, str(identifier) if identifier is not None else None, url, r.status_code, dur, payload)
        return payload, r.status_code
    except ValueError as e:
        return {"error": str(e)}, 400
    except requests.RequestException as e:
        return {"error": str(e)}, 500


def _get_latest_english_flavor_text(entries: List[Dict[str, Any]]) -> str:
    """Extract the most recent English Pokedex entry."""
    english_entries = [
        e for e in entries
        if e.get("language", {}).get("name") == "en"
    ]
    if english_entries:
        # Return the last one (usually most recent)
        return english_entries[-1].get("flavor_text", "").replace("\n", " ").replace("\f", " ")
    return ""


def _extract_id_from_url(url: str) -> Optional[int]:
    """Extract numeric ID from a PokeAPI URL."""
    if not isinstance(url, str):
        return None
    import re
    m = re.search(r"/(\d+)/?$", url)
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    return None


# ==================== ROOT ====================

@app.get("/")
def root() -> Response:
    """Serve the main HTML page."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    return send_file(index_path)


@app.get("/api")
def api_info() -> Response:
    """List all available API endpoints."""
    endpoints = {
        "info": "/api - This endpoint",
        "endpoints": sorted(ENDPOINTS),
        "routes": {
            "berries": [
                "/api/berry",
                "/api/berry/<id_or_name>",
                "/api/berry-firmness/<id_or_name>",
                "/api/berry-flavor/<id_or_name>",
            ],
            "contests": [
                "/api/contest-type/<id_or_name>",
                "/api/contest-effect/<id>",
                "/api/super-contest-effect/<id>",
            ],
            "encounters": [
                "/api/encounter-method/<id_or_name>",
                "/api/encounter-condition/<id_or_name>",
                "/api/encounter-condition-value/<id_or_name>",
            ],
            "evolution": [
                "/api/evolution-chain/<id>",
                "/api/evolution-trigger/<id_or_name>",
            ],
            "games": [
                "/api/generation",
                "/api/generation/<id_or_name>",
                "/api/generation/<int:gen_id>/species",
                "/api/pokedex/<id_or_name>",
                "/api/version/<id_or_name>",
                "/api/version-group/<id_or_name>",
            ],
            "items": [
                "/api/item",
                "/api/item/<id_or_name>",
                "/api/item-attribute/<id_or_name>",
                "/api/item-category/<id_or_name>",
                "/api/item-fling-effect/<id_or_name>",
                "/api/item-pocket/<id_or_name>",
            ],
            "locations": [
                "/api/location",
                "/api/location/<id_or_name>",
                "/api/location-area/<id_or_name>",
                "/api/pal-park-area/<id_or_name>",
                "/api/region",
                "/api/region/<id_or_name>",
            ],
            "machines": [
                "/api/machine/<id>",
            ],
            "moves": [
                "/api/move",
                "/api/move/<id_or_name>",
                "/api/move-ailment/<id_or_name>",
                "/api/move-battle-style/<id_or_name>",
                "/api/move-category/<id_or_name>",
                "/api/move-damage-class/<id_or_name>",
                "/api/move-learn-method/<id_or_name>",
                "/api/move-target/<id_or_name>",
            ],
            "pokemon": [
                "/api/pokemon",
                "/api/pokemon/<name_or_id>",
                "/api/pokemon/<name_or_id>/summary",
                "/api/pokemon/<name_or_id>/encounters",
                "/api/pokemon/<name_or_id>/sprite",
                "/api/ability",
                "/api/ability/<id_or_name>",
                "/api/characteristic/<id>",
                "/api/egg-group/<id_or_name>",
                "/api/gender/<id_or_name>",
                "/api/growth-rate/<id_or_name>",
                "/api/nature/<id_or_name>",
                "/api/pokeathlon-stat/<id_or_name>",
                "/api/pokemon-color/<id_or_name>",
                "/api/pokemon-form/<id_or_name>",
                "/api/pokemon-habitat/<id_or_name>",
                "/api/pokemon-shape/<id_or_name>",
                "/api/pokemon-species/<id_or_name>",
                "/api/stat/<id_or_name>",
                "/api/type",
                "/api/type/<id_or_name>",
            ],
            "utility": [
                "/api/language/<id_or_name>",
            ],
        }
    }
    return jsonify(endpoints)


# ==================== BERRIES ====================

@app.get("/api/berry")
@app.get("/api/berry/<identifier>")
def berry(identifier: str = None) -> Response:
    """Get berry list or specific berry."""
    payload, status = _proxy_endpoint("berry", identifier)
    return jsonify(payload), status


@app.get("/api/berry-firmness/<identifier>")
def berry_firmness(identifier: str) -> Response:
    """Get berry firmness."""
    payload, status = _proxy_endpoint("berry-firmness", identifier)
    return jsonify(payload), status


@app.get("/api/berry-flavor/<identifier>")
def berry_flavor(identifier: str) -> Response:
    """Get berry flavor."""
    payload, status = _proxy_endpoint("berry-flavor", identifier)
    return jsonify(payload), status


# ==================== CONTESTS ====================

@app.get("/api/contest-type/<identifier>")
def contest_type(identifier: str) -> Response:
    """Get contest type."""
    payload, status = _proxy_endpoint("contest-type", identifier)
    return jsonify(payload), status


@app.get("/api/contest-effect/<int:effect_id>")
def contest_effect(effect_id: int) -> Response:
    """Get contest effect."""
    payload, status = _proxy_endpoint("contest-effect", str(effect_id))
    return jsonify(payload), status


@app.get("/api/super-contest-effect/<int:effect_id>")
def super_contest_effect(effect_id: int) -> Response:
    """Get super contest effect."""
    payload, status = _proxy_endpoint("super-contest-effect", str(effect_id))
    return jsonify(payload), status


# ==================== ENCOUNTERS ====================

@app.get("/api/encounter-method/<identifier>")
def encounter_method(identifier: str) -> Response:
    """Get encounter method."""
    payload, status = _proxy_endpoint("encounter-method", identifier)
    return jsonify(payload), status


@app.get("/api/encounter-condition/<identifier>")
def encounter_condition(identifier: str) -> Response:
    """Get encounter condition."""
    payload, status = _proxy_endpoint("encounter-condition", identifier)
    return jsonify(payload), status


@app.get("/api/encounter-condition-value/<identifier>")
def encounter_condition_value(identifier: str) -> Response:
    """Get encounter condition value."""
    payload, status = _proxy_endpoint("encounter-condition-value", identifier)
    return jsonify(payload), status


# ==================== EVOLUTION ====================

@app.get("/api/evolution-chain/<int:chain_id>")
def evolution_chain(chain_id: int) -> Response:
    """Get evolution chain."""
    payload, status = _proxy_endpoint("evolution-chain", str(chain_id))
    return jsonify(payload), status


def _summarize_evolution_conditions_py(details: List[Dict[str, Any]]) -> List[str]:
    """Summarize evolution conditions to short chips."""
    if not isinstance(details, list) or not details:
        return ["level up"]
    d = details[0]
    chips: List[str] = []
    if d.get("min_level") is not None:
        chips.append(f"Lv {d.get('min_level')}")
    if d.get("item", {}).get("name"):
        chips.append(f"item: {d['item']['name']}")
    if d.get("held_item", {}).get("name"):
        chips.append(f"holds: {d['held_item']['name']}")
    trig = (d.get("trigger") or {}).get("name")
    if trig and "level-up" not in trig:
        chips.append(trig)
    if d.get("time_of_day"):
        chips.append(d["time_of_day"])
    if d.get("min_happiness") is not None:
        chips.append(f"happiness ≥ {d.get('min_happiness')}")
    if d.get("min_beauty") is not None:
        chips.append(f"beauty ≥ {d.get('min_beauty')}")
    if d.get("min_affection") is not None:
        chips.append(f"affection ≥ {d.get('min_affection')}")
    if (d.get("known_move") or {}).get("name"):
        chips.append(f"knows: {d['known_move']['name']}")
    if (d.get("known_move_type") or {}).get("name"):
        chips.append(f"move type: {d['known_move_type']['name']}")
    if (d.get("location") or {}).get("name"):
        chips.append(f"at: {d['location']['name']}")
    if d.get("needs_overworld_rain"):
        chips.append("raining")
    if (d.get("party_species") or {}).get("name"):
        chips.append(f"party: {d['party_species']['name']}")
    if (d.get("party_type") or {}).get("name"):
        chips.append(f"party type: {d['party_type']['name']}")
    if d.get("relative_physical_stats") is not None:
        chips.append(f"phys.stats: {d.get('relative_physical_stats')}")
    if (d.get("trade_species") or {}).get("name"):
        chips.append(f"trade for: {d['trade_species']['name']}")
    if d.get("turn_upside_down"):
        chips.append("hold console upside-down")
    if not chips:
        chips.append(trig or "evolves")
    return chips


def _build_evo_paths(node: Dict[str, Any], acc_steps: List[Dict[str, Any]], acc_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Recursively flatten evolution chain into linear paths."""
    sp = node.get("species") or {}
    name = sp.get("name")
    sid = _extract_id_from_url(sp.get("url"))
    sprite = sprite_url_build("pokemon", sid) if sid else ""
    step = {"key": f"{name}-{sid if sid is not None else 'x'}", "name": name, "id": sid, "sprite": sprite}
    steps_next = [*acc_steps, step]

    evolves_to = node.get("evolves_to") or []
    if not evolves_to:
        return [{"steps": steps_next, "links": acc_links}]

    paths: List[Dict[str, Any]] = []
    for ev in evolves_to:
        conds = _summarize_evolution_conditions_py(ev.get("evolution_details") or [])
        links_next = [*acc_links, {"conditions": conds}]
        paths.extend(_build_evo_paths(ev, steps_next, links_next))
    return paths


@app.get("/api/evolution-chain/<int:chain_id>/paths")
def evolution_chain_paths(chain_id: int) -> Response:
    """Return pre-parsed evolution paths with sprites and condition chips."""
    payload, status = _proxy_endpoint("evolution-chain", str(chain_id))
    if status != 200:
        return jsonify(payload), status
    root = payload.get("chain")
    if not root:
        return jsonify({"paths": []})
    paths = _build_evo_paths(root, [], [])
    # Filter degenerate paths
    paths = [p for p in paths if isinstance(p.get("steps"), list) and p["steps"]]
    return jsonify({"paths": paths, "chain_id": chain_id})


@app.get("/api/evolution-trigger/<identifier>")
def evolution_trigger(identifier: str) -> Response:
    """Get evolution trigger."""
    payload, status = _proxy_endpoint("evolution-trigger", identifier)
    return jsonify(payload), status


# ==================== GAMES ====================

@app.get("/api/generation")
@app.get("/api/generation/<identifier>")
def generation(identifier: str = None) -> Response:
    """Get generation list or specific generation."""
    if identifier is None:
        # Return enhanced list with IDs
        data = _http_get_json(api_url_build("generation") + "?limit=100")
        results: List[Dict[str, Any]] = []
        for r in data.get("results", []):
            url = r.get("url", "")
            name = r.get("name")
            gen_id = _extract_id_from_url(url)
            results.append({"id": gen_id or name, "name": name, "url": url})
        results.sort(key=lambda g: (not isinstance(g["id"], int), g["id"]))
        return jsonify({"results": results})

    payload, status = _proxy_endpoint("generation", identifier)
    return jsonify(payload), status


# Alias to match docs and README
@app.get("/api/generations")
def generations_alias() -> Response:
    return generation()  # type: ignore[misc]


@app.get("/api/generation/<int:gen_id>/species")
def generation_species(gen_id: int) -> Response:
    """Get all Pokemon species in a generation."""
    data = _http_get_json(api_url_build("generation", str(gen_id)))
    out: List[Dict[str, Any]] = []

    for s in data.get("pokemon_species", []):
        name = s.get("name")
        url = s.get("url", "")
        sid = _extract_id_from_url(url)
        sprite = sprite_url_build("pokemon", sid) if sid else ""
        out.append({"id": sid or name, "name": name, "sprite": sprite})

    out.sort(key=lambda a: a["name"])
    return jsonify({"results": out})


@app.get("/api/pokedex/<identifier>")
def pokedex(identifier: str) -> Response:
    """Get pokedex."""
    payload, status = _proxy_endpoint("pokedex", identifier)
    return jsonify(payload), status


@app.get("/api/version/<identifier>")
def version(identifier: str) -> Response:
    """Get version."""
    payload, status = _proxy_endpoint("version", identifier)
    return jsonify(payload), status


@app.get("/api/version-group/<identifier>")
def version_group(identifier: str) -> Response:
    """Get version group."""
    payload, status = _proxy_endpoint("version-group", identifier)
    return jsonify(payload), status


# ==================== ITEMS ====================

@app.get("/api/item")
@app.get("/api/item/<identifier>")
def item(identifier: str = None) -> Response:
    """Get item list or specific item."""
    payload, status = _proxy_endpoint("item", identifier)
    return jsonify(payload), status


@app.get("/api/item-attribute/<identifier>")
def item_attribute(identifier: str) -> Response:
    """Get item attribute."""
    payload, status = _proxy_endpoint("item-attribute", identifier)
    return jsonify(payload), status


@app.get("/api/item-category/<identifier>")
def item_category(identifier: str) -> Response:
    """Get item category."""
    payload, status = _proxy_endpoint("item-category", identifier)
    return jsonify(payload), status


@app.get("/api/item-fling-effect/<identifier>")
def item_fling_effect(identifier: str) -> Response:
    """Get item fling effect."""
    payload, status = _proxy_endpoint("item-fling-effect", identifier)
    return jsonify(payload), status


@app.get("/api/item-pocket/<identifier>")
def item_pocket(identifier: str) -> Response:
    """Get item pocket."""
    payload, status = _proxy_endpoint("item-pocket", identifier)
    return jsonify(payload), status


# ==================== LOCATIONS ====================

@app.get("/api/location")
@app.get("/api/location/<identifier>")
def location(identifier: str = None) -> Response:
    """Get location list or specific location."""
    payload, status = _proxy_endpoint("location", identifier)
    return jsonify(payload), status


@app.get("/api/location-area/<identifier>")
def location_area(identifier: str) -> Response:
    """Get location area."""
    payload, status = _proxy_endpoint("location-area", identifier)
    return jsonify(payload), status


@app.get("/api/pal-park-area/<identifier>")
def pal_park_area(identifier: str) -> Response:
    """Get pal park area."""
    payload, status = _proxy_endpoint("pal-park-area", identifier)
    return jsonify(payload), status


@app.get("/api/region")
@app.get("/api/region/<identifier>")
def region(identifier: str = None) -> Response:
    """Get region list or specific region."""
    payload, status = _proxy_endpoint("region", identifier)
    return jsonify(payload), status


# ==================== MACHINES ====================

@app.get("/api/machine/<int:machine_id>")
def machine(machine_id: int) -> Response:
    """Get machine (TM/HM)."""
    payload, status = _proxy_endpoint("machine", str(machine_id))
    return jsonify(payload), status


# ==================== MOVES ====================

@app.get("/api/move")
@app.get("/api/move/<identifier>")
def move(identifier: str = None) -> Response:
    """Get move list or specific move."""
    payload, status = _proxy_endpoint("move", identifier)
    return jsonify(payload), status


@app.get("/api/move-ailment/<identifier>")
def move_ailment(identifier: str) -> Response:
    """Get move ailment."""
    payload, status = _proxy_endpoint("move-ailment", identifier)
    return jsonify(payload), status


@app.get("/api/move-battle-style/<identifier>")
def move_battle_style(identifier: str) -> Response:
    """Get move battle style."""
    payload, status = _proxy_endpoint("move-battle-style", identifier)
    return jsonify(payload), status


@app.get("/api/move-category/<identifier>")
def move_category(identifier: str) -> Response:
    """Get move category."""
    payload, status = _proxy_endpoint("move-category", identifier)
    return jsonify(payload), status


@app.get("/api/move-damage-class/<identifier>")
def move_damage_class(identifier: str) -> Response:
    """Get move damage class."""
    payload, status = _proxy_endpoint("move-damage-class", identifier)
    return jsonify(payload), status


@app.get("/api/move-learn-method/<identifier>")
def move_learn_method(identifier: str) -> Response:
    """Get move learn method."""
    payload, status = _proxy_endpoint("move-learn-method", identifier)
    return jsonify(payload), status


@app.get("/api/move-target/<identifier>")
def move_target(identifier: str) -> Response:
    """Get move target."""
    payload, status = _proxy_endpoint("move-target", identifier)
    return jsonify(payload), status


# ==================== POKEMON ====================

@app.get("/api/pokemon")
def pokemon_list() -> Response:
    """Get paginated list of all Pokemon."""
    limit = flask.request.args.get("limit", default=20, type=int)
    offset = flask.request.args.get("offset", default=0, type=int)
    url = api_url_build("pokemon") + f"?limit={limit}&offset={offset}"
    try:
        data = _http_get_json(url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/pokemon/<name_or_id>")
def pokemon(name_or_id: str) -> Response:
    """Get specific Pokemon data."""
    url = POKEAPI_BASE + name_or_id.strip().lower()
    t0 = time.perf_counter()
    r = requests.get(url, timeout=10.0)
    dur = (time.perf_counter() - t0) * 1000.0
    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
    _save_api_call(_now_iso(), "pokemon", name_or_id, url, r.status_code, dur, payload)
    return jsonify(payload), r.status_code


@app.get("/api/pokemon/<name_or_id>/summary")
def pokemon_summary(name_or_id: str) -> Response:
    """Get a human-readable summary of Pokemon."""
    url = POKEAPI_BASE + name_or_id.strip().lower()
    t0 = time.perf_counter()
    r = requests.get(url, timeout=10.0)
    dur = (time.perf_counter() - t0) * 1000.0
    if r.status_code != 200:
        try:
            payload = r.json()
        except Exception:
            payload = {"error": r.text}
        _save_api_call(_now_iso(), "pokemon", name_or_id, url, r.status_code, dur, payload)
        return jsonify(payload), r.status_code
    data = r.json()
    text = summarize_pokemon(data)
    _save_api_call(_now_iso(), "pokemon", name_or_id, url, r.status_code, dur, data)
    return jsonify({"summary": text, "name_or_id": name_or_id, "id": data.get("id")})


@app.get("/api/pokemon/<name_or_id>/sprite")
def pokemon_sprite(name_or_id: str) -> Response:
    """Get Pokemon sprite URL with optional parameters."""
    # First get the pokemon ID
    url = POKEAPI_BASE + name_or_id.strip().lower()
    t0 = time.perf_counter()
    r = requests.get(url, timeout=10.0)
    dur = (time.perf_counter() - t0) * 1000.0
    if r.status_code != 200:
        try:
            payload = r.json()
        except Exception:
            payload = {"error": r.text}
        _save_api_call(_now_iso(), "pokemon", name_or_id, url, r.status_code, dur, payload)
        return jsonify({"error": "Pokemon not found"}), 404

    data = r.json()
    _save_api_call(_now_iso(), "pokemon", name_or_id, url, r.status_code, dur, data)
    pokemon_id = data.get("id")

    # Parse sprite options from query parameters
    sprite_options = {
        "back": flask.request.args.get("back", "false").lower() == "true",
        "shiny": flask.request.args.get("shiny", "false").lower() == "true",
        "female": flask.request.args.get("female", "false").lower() == "true",
        "model": flask.request.args.get("model", "false").lower() == "true",
        "other": flask.request.args.get("other", "false").lower() == "true",
        "official_artwork": flask.request.args.get("official_artwork", "false").lower() == "true",
        "dream_world": flask.request.args.get("dream_world", "false").lower() == "true",
    }

    sprite_url = sprite_url_build("pokemon", pokemon_id, **sprite_options)

    return jsonify({
        "pokemon": name_or_id,
        "id": pokemon_id,
        "sprite_url": sprite_url,
        "options": sprite_options
    })


@app.get("/api/pokemon/<name_or_id>/encounters")
def pokemon_encounters(name_or_id: str) -> Response:
    """Get Pokemon location area encounters (full or summary)."""
    full = flask.request.args.get("full", "false").lower() == "true"

    url = f"{POKEAPI_BASE}{name_or_id.strip().lower()}/encounters"
    t0 = time.perf_counter()
    r = requests.get(url, timeout=10.0)
    dur = (time.perf_counter() - t0) * 1000.0

    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
        _save_api_call(_now_iso(), "pokemon-encounters", name_or_id, url, r.status_code, dur, payload)
        return jsonify(payload), r.status_code

    if r.status_code != 200 or full:
        _save_api_call(_now_iso(), "pokemon-encounters", name_or_id, url, r.status_code, dur, payload)
        return jsonify(payload), r.status_code

    # Return simplified summary
    if not isinstance(payload, list):
        return jsonify(payload), r.status_code

    summary = {
        "pokemon": name_or_id,
        "total_locations": len(payload),
        "locations": []
    }

    for encounter in payload:
        location_name = encounter.get("location_area", {}).get("name", "unknown")
        version_details = encounter.get("version_details", [])

        # Simplify version details
        versions = []
        for vd in version_details:
            version_name = vd.get("version", {}).get("name", "unknown")
            max_chance = vd.get("max_chance", 0)
            encounter_details = vd.get("encounter_details", [])

            methods = list(set(
                ed.get("method", {}).get("name", "unknown")
                for ed in encounter_details
            ))

            versions.append({
                "version": version_name,
                "max_chance": max_chance,
                "methods": methods
            })

        summary["locations"].append({
            "location": location_name,
            "versions": versions
        })

    summary["full_url"] = f"/api/pokemon/{name_or_id}/encounters?full=true"

    # Log the summarized call as well for convenience
    _save_api_call(_now_iso(), "pokemon-encounters", name_or_id, url, r.status_code, dur, summary)

    return jsonify(summary), r.status_code


@app.get("/api/ability")
@app.get("/api/ability/<identifier>")
def ability(identifier: str = None) -> Response:
    """Get ability list or specific ability."""
    payload, status = _proxy_endpoint("ability", identifier)
    return jsonify(payload), status


@app.get("/api/characteristic/<int:char_id>")
def characteristic(char_id: int) -> Response:
    """Get characteristic."""
    payload, status = _proxy_endpoint("characteristic", str(char_id))
    return jsonify(payload), status


@app.get("/api/egg-group/<identifier>")
def egg_group(identifier: str) -> Response:
    """Get egg group."""
    payload, status = _proxy_endpoint("egg-group", identifier)
    return jsonify(payload), status


@app.get("/api/gender/<identifier>")
def gender(identifier: str) -> Response:
    """Get gender."""
    payload, status = _proxy_endpoint("gender", identifier)
    return jsonify(payload), status


@app.get("/api/growth-rate/<identifier>")
def growth_rate(identifier: str) -> Response:
    """Get growth rate."""
    payload, status = _proxy_endpoint("growth-rate", identifier)
    return jsonify(payload), status


@app.get("/api/nature/<identifier>")
def nature(identifier: str) -> Response:
    """Get nature."""
    payload, status = _proxy_endpoint("nature", identifier)
    return jsonify(payload), status


@app.get("/api/pokeathlon-stat/<identifier>")
def pokeathlon_stat(identifier: str) -> Response:
    """Get pokeathlon stat."""
    payload, status = _proxy_endpoint("pokeathlon-stat", identifier)
    return jsonify(payload), status


@app.get("/api/pokemon-color/<identifier>")
def pokemon_color(identifier: str) -> Response:
    """Get pokemon color."""
    payload, status = _proxy_endpoint("pokemon-color", identifier)
    return jsonify(payload), status


@app.get("/api/pokemon-form/<identifier>")
def pokemon_form(identifier: str) -> Response:
    """Get pokemon form."""
    payload, status = _proxy_endpoint("pokemon-form", identifier)
    return jsonify(payload), status


@app.get("/api/pokemon-habitat/<identifier>")
def pokemon_habitat(identifier: str) -> Response:
    """Get pokemon habitat."""
    payload, status = _proxy_endpoint("pokemon-habitat", identifier)
    return jsonify(payload), status


@app.get("/api/pokemon-shape/<identifier>")
def pokemon_shape(identifier: str) -> Response:
    """Get pokemon shape."""
    payload, status = _proxy_endpoint("pokemon-shape", identifier)
    return jsonify(payload), status


@app.get("/api/pokemon-species/<identifier>")
def pokemon_species(identifier: str) -> Response:
    """Get pokemon species (full data or summary)."""
    full = flask.request.args.get("full", "false").lower() == "true"

    payload, status = _proxy_endpoint("pokemon-species", identifier)

    if status != 200 or full:
        return jsonify(payload), status

    # Return summarized version by default
    summary = {
        "id": payload.get("id"),
        "name": payload.get("name"),
        "order": payload.get("order"),
        "gender_rate": payload.get("gender_rate"),
        "capture_rate": payload.get("capture_rate"),
        "base_happiness": payload.get("base_happiness"),
        "is_baby": payload.get("is_baby"),
        "is_legendary": payload.get("is_legendary"),
        "is_mythical": payload.get("is_mythical"),
        "hatch_counter": payload.get("hatch_counter"),
        "has_gender_differences": payload.get("has_gender_differences"),
        "forms_switchable": payload.get("forms_switchable"),
        "growth_rate": payload.get("growth_rate"),
        "egg_groups": payload.get("egg_groups"),
        "color": payload.get("color"),
        "shape": payload.get("shape"),
        "evolves_from_species": payload.get("evolves_from_species"),
        "evolution_chain": payload.get("evolution_chain"),
        "habitat": payload.get("habitat"),
        "generation": payload.get("generation"),
        "names": payload.get("names"),
        "genera": payload.get("genera"),
        "varieties": payload.get("varieties"),
        # Only English flavor text from latest version
        "flavor_text": _get_latest_english_flavor_text(payload.get("flavor_text_entries", [])),
        "full_url": f"/api/pokemon-species/{identifier}?full=true"
    }

    return jsonify(summary), status


@app.get("/api/stat/<identifier>")
def stat(identifier: str) -> Response:
    """Get stat."""
    payload, status = _proxy_endpoint("stat", identifier)
    return jsonify(payload), status


@app.get("/api/type")
@app.get("/api/type/<identifier>")
def type_endpoint(identifier: str = None) -> Response:
    """Get type list or specific type."""
    payload, status = _proxy_endpoint("type", identifier)
    return jsonify(payload), status


# ==================== UTILITY ====================

@app.get("/api/language/<identifier>")
def language(identifier: str) -> Response:
    """Get language."""
    payload, status = _proxy_endpoint("language", identifier)
    return jsonify(payload), status


# ==================== RUN ====================

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
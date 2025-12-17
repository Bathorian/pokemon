from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
import flask
from flask import Flask, jsonify, send_file, Response
from flask_cors import CORS

from main import summarize_pokemon, POKEAPI_BASE

app = Flask(__name__, static_folder=None)
CORS(app)

# Base URLs for different resource types
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"


def _http_get_json(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Helper to fetch JSON from a URL."""
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _proxy_endpoint(resource_type: str, identifier: str = None, timeout: float = 10.0) -> tuple[Dict[str, Any], int]:
    """
    Generic proxy to PokeAPI endpoints.
    If identifier is None, returns a paginated list.
    Otherwise, returns the specific resource.
    """
    if identifier:
        url = f"{POKEAPI_BASE_URL}/{resource_type}/{identifier.strip().lower()}"
    else:
        url = f"{POKEAPI_BASE_URL}/{resource_type}"

    try:
        r = requests.get(url, timeout=timeout)
        try:
            payload = r.json()
        except Exception:
            payload = {"error": r.text}
        return payload, r.status_code
    except requests.RequestException as e:
        return {"error": str(e)}, 500


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
        data = _http_get_json(f"{POKEAPI_BASE_URL}/generation?limit=100")
        results: List[Dict[str, Any]] = []
        for r in data.get("results", []):
            url = r.get("url", "")
            name = r.get("name")
            gen_id = None
            if isinstance(url, str):
                import re
                m = re.search(r"/(\d+)/?$", url)
                if m:
                    try:
                        gen_id = int(m.group(1))
                    except ValueError:
                        gen_id = None
            results.append({"id": gen_id or name, "name": name, "url": url})
        results.sort(key=lambda g: (isinstance(g["id"], int), g["id"]))
        return jsonify({"results": results})

    payload, status = _proxy_endpoint("generation", identifier)
    return jsonify(payload), status


@app.get("/api/generation/<int:gen_id>/species")
def generation_species(gen_id: int) -> Response:
    """Get all Pokemon species in a generation."""
    data = _http_get_json(f"{POKEAPI_BASE_URL}/generation/{gen_id}")
    out: List[Dict[str, Any]] = []
    for s in data.get("pokemon_species", []):
        name = s.get("name")
        url = s.get("url", "")
        sid = None
        if isinstance(url, str):
            import re
            m = re.search(r"/(\d+)/?$", url)
            if m:
                try:
                    sid = int(m.group(1))
                except ValueError:
                    sid = None
        sprite = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{sid}.png" if sid else ""
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
    url = f"{POKEAPI_BASE_URL}/pokemon?limit={limit}&offset={offset}"
    try:
        data = _http_get_json(url)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.get("/api/pokemon/<name_or_id>")
def pokemon(name_or_id: str) -> Response:
    """Get specific Pokemon data."""
    url = POKEAPI_BASE + name_or_id.strip().lower()
    r = requests.get(url, timeout=10.0)
    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
    return jsonify(payload), r.status_code


@app.get("/api/pokemon/<name_or_id>/summary")
def pokemon_summary(name_or_id: str) -> Response:
    """Get a human-readable summary of Pokemon."""
    url = POKEAPI_BASE + name_or_id.strip().lower()
    r = requests.get(url, timeout=10.0)
    if r.status_code != 200:
        try:
            payload = r.json()
        except Exception:
            payload = {"error": r.text}
        return jsonify(payload), r.status_code
    data = r.json()
    text = summarize_pokemon(data)
    return jsonify({"summary": text, "name_or_id": name_or_id, "id": data.get("id")})


@app.get("/api/pokemon/<name_or_id>/encounters")
def pokemon_encounters(name_or_id: str) -> Response:
    """Get Pokemon location area encounters."""
    url = f"{POKEAPI_BASE}{name_or_id.strip().lower()}/encounters"
    r = requests.get(url, timeout=10.0)
    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
    return jsonify(payload), r.status_code


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
    """Get pokemon species."""
    payload, status = _proxy_endpoint("pokemon-species", identifier)
    return jsonify(payload), status


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
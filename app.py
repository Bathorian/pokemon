from __future__ import annotations

import os
from typing import Any, Dict, List

import requests
import flask
from flask import Flask, jsonify, send_file, Response
from flask_cors import CORS

from main import summarize_pokemon, POKEAPI_BASE  # reuse existing logic


app = Flask(__name__, static_folder=None)
CORS(app)


POKEAPI_GENERATIONS = "https://pokeapi.co/api/v2/generation"


def _http_get_json(url: str, timeout: float = 10.0) -> Dict[str, Any]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.json()


@app.get("/")
def root() -> Response:
    # Serve the existing static page for convenience
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    return send_file(index_path)


@app.get("/api/generations")
def generations() -> Response:
    data = _http_get_json(f"{POKEAPI_GENERATIONS}?limit=100")
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
    # sort by numeric id when possible
    results.sort(key=lambda g: (isinstance(g["id"], int), g["id"]))
    return jsonify({"results": results})


@app.get("/api/generation/<int:gen_id>/species")
def generation_species(gen_id: int) -> Response:
    data = _http_get_json(f"{POKEAPI_GENERATIONS}/{gen_id}")
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
    # alpha sort by name
    out.sort(key=lambda a: a["name"]) 
    return jsonify({"results": out})


@app.get("/api/pokemon/<name_or_id>")
def pokemon(name_or_id: str) -> Response:
    url = POKEAPI_BASE + name_or_id.strip().lower()
    r = requests.get(url, timeout=10.0)
    # pass through status codes (e.g., 404)
    try:
        payload = r.json()
    except Exception:
        payload = {"error": r.text}
    return jsonify(payload), r.status_code


@app.get("/api/pokemon/<name_or_id>/summary")
def pokemon_summary(name_or_id: str) -> Response:
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


if __name__ == "__main__":
    # Run the development server: python app.py
    app.run(host="127.0.0.1", port=5000, debug=True)

import json
import sys
from typing import Any, Dict, Optional

try:
    import requests
except Exception as e:  # pragma: no cover
    requests = None  # type: ignore


POKEAPI_BASE = "https://pokeapi.co/api/v2/pokemon/"


class PokeAPIError(Exception):
    pass


def fetch_pokemon(name_or_id: str, timeout: float = 10.0) -> Dict[str, Any]:

    if requests is None:
        raise PokeAPIError(
            "The 'requests' package is required. Please install dependencies with 'pip install -r requirements.txt'."
        )

    url = POKEAPI_BASE + str(name_or_id).strip().lower()
    try:
        resp = requests.get(url, timeout=timeout)
    except requests.RequestException as exc:  # type: ignore[attr-defined]
        raise PokeAPIError(f"Network error while calling PokeAPI: {exc}") from exc

    if resp.status_code == 404:
        raise PokeAPIError(f"Pokémon '{name_or_id}' not found (404).")
    if resp.status_code != 200:
        raise PokeAPIError(f"PokeAPI returned {resp.status_code}: {resp.text[:200]}")

    try:
        return resp.json()
    except json.JSONDecodeError as exc:
        raise PokeAPIError("Failed to parse PokeAPI response as JSON.") from exc


def summarize_pokemon(data: Dict[str, Any]) -> str:
    """Create a human-friendly summary string from PokeAPI Pokémon JSON."""
    name = data.get("name", "unknown")
    poke_id = data.get("id", "?")
    height = data.get("height", "?")
    weight = data.get("weight", "?")
    base_exp = data.get("base_experience")
    is_default = data.get("is_default")
    order = data.get("order")

    stats = {s.get("stat", {}).get("name", "stat"): s.get("base_stat", 0) for s in data.get("stats", [])}

    lines: list[str] = [
        f"Name: {name}",
        f"ID: {poke_id}",
        f"Height: {height}",
        f"Weight: {weight}",
    ]

    if base_exp is not None:
        lines.append(f"Base experience: {base_exp}")
    if order is not None:
        lines.append(f"Order: {order}")
    if is_default is not None:
        lines.append(f"Is default: {is_default}")

    # Species (name, url)
    species = data.get("species") or {}
    if isinstance(species, dict) and species:
        sp_name = species.get("name")
        sp_url = species.get("url")
        if sp_name or sp_url:
            pieces = [p for p in [sp_name, sp_url] if p]
            lines.append("Species: " + ", ".join(pieces))

    # Location encounters URL
    encounters_url = data.get("location_area_encounters")
    if encounters_url:
        lines.append(f"Encounters: {encounters_url}")

    # Types with slots
    typed = data.get("types") or []
    if isinstance(typed, list) and typed:
        t_desc: list[str] = []
        for t in typed:
            slot = t.get("slot")
            tname = (t.get("type") or {}).get("name")
            if slot is not None and tname:
                t_desc.append(f"[{slot}] {tname}")
            elif tname:
                t_desc.append(str(tname))
        if t_desc:
            lines.append("Types: " + ", ".join(t_desc))
    else:
        lines.append("Types: n/a")

    # Abilities with hidden/slot
    abil_list = data.get("abilities") or []
    if isinstance(abil_list, list) and abil_list:
        a_desc: list[str] = []
        for a in abil_list:
            aname = (a.get("ability") or {}).get("name")
            hidden = a.get("is_hidden")
            slot = a.get("slot")
            part = aname or "unknown"
            meta = []
            if hidden is not None:
                meta.append(f"hidden={hidden}")
            if slot is not None:
                meta.append(f"slot={slot}")
            if meta:
                part += " (" + ", ".join(meta) + ")"
            a_desc.append(part)
        if a_desc:
            lines.append("Abilities: " + ", ".join(a_desc))
    else:
        lines.append("Abilities: n/a")

    # Base stats
    lines.append("Base stats:")
    for stat_name, value in stats.items():
        lines.append(f"  - {stat_name}: {value}")

    # Sprites
    sprite: Optional[str] = None
    sprites = data.get("sprites") or {}
    if isinstance(sprites, dict):
        sprite = sprites.get("front_default")
    if sprite:
        lines.append(f"Sprite: {sprite}")

    if isinstance(sprites, dict):
        extra_keys = [
            "back_default",
            "front_shiny",
            "back_shiny",
            "front_female",
            "back_female",
            "front_shiny_female",
            "back_shiny_female",
        ]
        extras = []
        for k in extra_keys:
            v = sprites.get(k)
            if v:
                extras.append(f"{k}: {v}")
        if extras:
            lines.append("Sprites (more):")
            for e in extras:
                lines.append(f"  - {e}")

    # Held items (names only)
    held_items = data.get("held_items") or []
    if isinstance(held_items, list) and held_items:
        item_names: list[str] = []
        for hi in held_items:
            iname = (hi.get("item") or {}).get("name")
            if iname:
                item_names.append(str(iname))
        if item_names:
            lines.append("Held items: " + ", ".join(item_names))

    # Forms (names)
    forms = data.get("forms") or []
    if isinstance(forms, list) and forms:
        form_names: list[str] = []
        for f in forms:
            fname = f.get("name")
            if fname:
                form_names.append(str(fname))
        if form_names:
            lines.append("Forms: " + ", ".join(form_names))

    # Cries (latest/legacy)
    cries = data.get("cries") or {}
    if isinstance(cries, dict) and cries:
        latest = cries.get("latest")
        legacy = cries.get("legacy")
        if latest or legacy:
            lines.append("Cries:")
            if latest:
                lines.append(f"  - latest: {latest}")
            if legacy:
                lines.append(f"  - legacy: {legacy}")

    # Past types (count only to avoid verbosity)
    past_types = data.get("past_types") or []
    if isinstance(past_types, list) and past_types:
        lines.append(f"Past types entries: {len(past_types)}")

    return "\n".join(lines)


def _parse_args(argv: list[str]) -> Dict[str, Any]:
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch and display information about a Pokémon from PokeAPI"
    )
    parser.add_argument(
        "name",
        nargs="?",
        help="Pokémon name or ID (if omitted, you'll be prompted; appended to base API URL)",
    )
    parser.add_argument(
        "--raw-json",
        action="store_true",
        help="Print raw JSON instead of a summary",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Network timeout in seconds (default: 10)",
    )

    ns = parser.parse_args(argv)
    return {"name": ns.name, "raw_json": ns.raw_json, "timeout": ns.timeout}


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    # If name not provided via CLI, prompt the user interactively
    name = (args.get("name") or "").strip() if isinstance(args, dict) else ""
    while not name:
        try:
            name = input("Enter Pokémon name or ID: ").strip()
        except EOFError:
            print("Error: No input provided.", file=sys.stderr)
            return 2
    args["name"] = name
    try:
        data = fetch_pokemon(args["name"], timeout=args["timeout"])
    except PokeAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args["raw_json"]:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(summarize_pokemon(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

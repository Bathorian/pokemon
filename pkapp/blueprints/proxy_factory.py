from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple
from flask import Blueprint, jsonify, Response

# Each tuple: (rule, endpoint_key, has_identifier)
ProxyRule = Tuple[str, str, bool]


def create_proxy_blueprint(
    name: str,
    url_prefix: str,
    rules: Sequence[ProxyRule],
    proxy_func: Callable[[str, Optional[str]], tuple[object, int]],
) -> Blueprint:
    """Build a small blueprint registering proxy routes defined by rules.

    proxy_func should return (payload, status_code).
    """
    bp = Blueprint(name, __name__, url_prefix=url_prefix)

    def make_view(endpoint_key: str, has_identifier: bool):
        def view(identifier: Optional[str] = None) -> Response:
            payload, status = proxy_func(endpoint_key, identifier)
            return jsonify(payload), status
        return view

    for rule, endpoint_key, has_identifier in rules:
        view_func = make_view(endpoint_key, has_identifier)
        endpoint_name = f"{name}_{endpoint_key}".replace('-', '_')
        if has_identifier:
            bp.add_url_rule(rule + "/<identifier>", endpoint=endpoint_name, view_func=view_func, methods=["GET"])
        else:
            bp.add_url_rule(rule, endpoint=endpoint_name, view_func=view_func, methods=["GET"])

    return bp

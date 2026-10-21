"""Bound the anonymous simulation's HTTP surface and expensive work.

These worker-local limits are a small-instance safeguard, not a DDoS service.
There is no authentication or real-device authorization in this public demo.
"""
from pathlib import Path
from threading import BoundedSemaphore, Lock
from time import monotonic
from urllib.parse import urlsplit
import json
import math
import os

from flask import abort, g, request
from werkzeug.exceptions import HTTPException

from energy import DEFAULT, DEVICES, ROOMS
from runtime import step


MAX_BODY = 256 * 1024


def number(value, low=-1e12, high=1e12):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def bounded_json(value):
    """Check before traversing nested client state or passing it to Dash."""
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 10000 or depth > 16:
            return False
        if isinstance(item, dict):
            if len(item) > 128 or any(len(key) > 2048 for key in item):
                return False
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            if len(item) > 128:
                return False
            pending.extend((child, depth + 1) for child in item)
        elif isinstance(item, str):
            if len(item) > 8192:
                return False
        elif item is not None and type(item) is not bool and not number(item):
            return False
    return True


def same_shape(value, sample):
    """Validate complete snapshots; clients may not invent nested structures."""
    if isinstance(sample, dict):
        return (isinstance(value, dict) and value.keys() == sample.keys()
                and all(same_shape(value[key], item) for key, item in sample.items()))
    if isinstance(sample, list):
        return isinstance(value, list) and len(value) <= 90 and all(same_shape(item, sample[0]) for item in value)
    if type(sample) is bool:
        return type(value) is bool
    if isinstance(sample, str):
        return isinstance(value, str) and len(value) <= 256
    return number(value)


class RequestBudget:
    """One bounded token bucket; never trust spoofable client-IP headers."""
    def __init__(self, capacity=240, refill=60):
        self.capacity, self.refill = capacity, refill
        self.tokens, self.last = float(capacity), monotonic()
        self.lock = Lock()

    def take(self):
        now = monotonic()
        with self.lock:
            self.tokens = min(self.capacity, self.tokens + max(0, now - self.last) * self.refill)
            self.last = now
            if self.tokens < 1:
                return False
            self.tokens -= 1
            return True


def install(app):
    """Call after registering callbacks and before serving any requests."""
    server = app.server
    public_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip().lower()
    public_origin = os.getenv("PUBLIC_ORIGIN", f"https://{public_host}" if public_host else "").rstrip("/")
    parsed = urlsplit(public_origin)
    if public_origin and (parsed.scheme != "https" or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username):
        raise ValueError("PUBLIC_ORIGIN must be an HTTPS origin without a path or credentials")
    if parsed.hostname:
        public_host = parsed.hostname
    server.config.update(MAX_CONTENT_LENGTH=MAX_BODY, MAX_FORM_MEMORY_SIZE=MAX_BODY,
                         MAX_FORM_PARTS=16, TRUSTED_HOSTS=["localhost", "127.0.0.1"] + ([public_host] if public_host else []))
    budget = RequestBudget()
    work = BoundedSemaphore(2)
    layouts = BoundedSemaphore(2)
    server.extensions["simulation_guard"] = {"budget": budget, "work": work, "layouts": layouts}
    assets = {"/assets/" + file.relative_to(app.config.assets_folder).as_posix()
              for file in Path(app.config.assets_folder).rglob("*")
              if file.is_file() and file.suffix.lower() in (".css", ".svg", ".png", ".ico", ".jpg", ".woff2")}
    snapshot_sample = step(DEFAULT)
    pattern_ids = [component.id for component in app.layout._traverse()
                   if isinstance(getattr(component, "id", None), dict)]
    components = {component.id: component.to_plotly_json()["props"]
                  for component in app.layout._traverse() if isinstance(getattr(component, "id", None), str)}
    csp = "; ".join([
        "default-src 'self'", "script-src 'self' " + " ".join(app.csp_hashes()),
        "style-src 'self' 'unsafe-inline'", "img-src 'self' data: blob:",
        "font-src 'self' data:", "connect-src 'self'", "worker-src 'self' blob:",
        "object-src 'none'", "base-uri 'none'", "frame-ancestors 'none'", "form-action 'self'",
    ])

    def pattern_members(pattern):
        if isinstance(pattern, str):
            pattern = json.loads(pattern)
        return [item for item in pattern_ids if item.keys() == pattern.keys()
                and all(value == ["ALL"] or item[key] == value for key, value in pattern.items())]

    def valid_value(component_id, prop, value):
        if component_id.startswith("{"):
            members = pattern_members(component_id)
            if not isinstance(value, list) or len(value) != len(members):
                return False
            pattern = json.loads(component_id)
            if prop == "id":
                return value == members
            if prop == "n_clicks":
                return all(item is None or number(item, 0, 1e9) for item in value)
            if pattern["type"] == "brightness":
                return all(number(item, 0, 100) for item in value)
            return all(isinstance(item, list) and all(option == "on" for option in item) and len(item) <= 1 for item in value)
        if prop in ("clickInfo", "hoverInfo"):
            return value is None or (isinstance(value, dict) and isinstance(value.get("representationId", ""), str))
        if prop in ("n_clicks", "n_intervals"):
            return value is None or number(value, 0, 1e9)
        if prop == "data":
            if component_id == "scenario":
                return same_shape(value, DEFAULT)
            if component_id == "live-state":
                return value == {} or (same_shape(value, snapshot_sample) and number(value["seconds"], 0, 86400)
                    and number(value["index"], 0, 95) and value["mode"] in ("irish", "play", "manual"))
            if component_id == "device-overrides":
                return isinstance(value, dict) and all(
                    (key in DEVICES and item in ("on", "off", "auto")) or
                    (key == "_light_levels" and isinstance(item, dict) and all(k in ROOMS and number(v, 0, 100) for k, v in item.items()))
                    for key, item in value.items())
            if component_id == "scene-memory":
                return isinstance(value, dict) and all(key in ("home", "devices", "grid") and isinstance(item, dict)
                    and set(item) <= {"mode", "signature"} and item.get("mode") in ("exterior", "interior", "xray")
                    and isinstance(item.get("signature", ""), str) for key, item in value.items())
            if component_id.endswith("-zoom"):
                return isinstance(value, dict) and set(value) <= {"factor", "action", "sequence"} and number(value.get("factor", 1), .55, 3.5) and value.get("action", "initial") in ("initial", "reset", "zoom") and number(value.get("sequence", 0), 0, 1e9)
            return number(value, 0, 95)
        props = components.get(component_id, {})
        if prop == "value":
            if "options" in props:
                options = [item.get("value") if isinstance(item, dict) else item for item in props["options"]]
                return (all(item in options for item in value) and len(value) <= len(options)) if isinstance(value, list) else value in options
            return value is None or number(value, props.get("min", 0), props.get("max", 100))
        return False

    def output_matches(received, expected):
        if isinstance(expected.component_id, dict):
            pattern = json.loads(expected.component_id_str())
            members = pattern_members(pattern)
            return isinstance(received, list) and len(received) == len(members) and all(
                item == {"id": member, "property": expected.component_property} for item, member in zip(received, members))
        return received == {"id": expected.component_id, "property": expected.component_property}

    def valid_callback(data):
        if not isinstance(data, dict) or not bounded_json(data):
            return False
        metadata = app.callback_map.get(data.get("output")) if isinstance(data.get("output"), str) else None
        if not metadata:
            return False
        for group in ("inputs", "state"):
            values = data.get(group, [])
            if not isinstance(values, list) or len(values) != len(metadata[group]):
                return False
            for item, spec in zip(values, metadata[group]):
                # Dash's browser expands ALL dependencies into a nested list
                # of concrete component records. Pure HTTP clients can also
                # use the equivalent wildcard record with an array value.
                if isinstance(item, list) and spec["id"].startswith("{"):
                    members = pattern_members(spec["id"])
                    if len(item) != len(members) or any(not isinstance(child, dict)
                            or child.get("id") != member or child.get("property") != spec["property"]
                            for child, member in zip(item, members)):
                        return False
                    if not valid_value(spec["id"], spec["property"], [child.get("value") for child in item]):
                        return False
                    continue
                if (not isinstance(item, dict) or item.get("id") != spec["id"] or item.get("property") != spec["property"]
                        or not valid_value(spec["id"], spec["property"], item.get("value"))):
                    return False
        outputs, expected = data.get("outputs"), metadata["output"]
        if isinstance(expected, list):
            if not isinstance(outputs, list) or len(outputs) != len(expected) or not all(output_matches(item, spec) for item, spec in zip(outputs, expected)):
                return False
        elif not output_matches(outputs, expected):
            return False
        changed = data.get("changedPropIds", [])
        if not isinstance(changed, list) or len(changed) > len(metadata["inputs"]) + 12:
            return False
        allowed = set()
        for spec in metadata["inputs"]:
            ids = pattern_members(spec["id"]) if spec["id"].startswith("{") else [spec["id"]]
            allowed.update((json.dumps(item, sort_keys=True, separators=(",", ":")) if isinstance(item, dict) else item) + "." + spec["property"] for item in ids)
            allowed.add(spec["id"] + "." + spec["property"])
        return all(isinstance(item, str) and item in allowed for item in changed)

    @server.before_request
    def guard():
        path = request.path
        if len(request.query_string) > 2048:
            abort(400)
        if request.method not in ("GET", "HEAD", "POST", "OPTIONS"):
            abort(405)
        if request.method in ("POST", "OPTIONS"):
            if path != "/_dash-update-component":
                abort(405)
            origin = request.headers.get("Origin")
            local_origin = request.host_url.rstrip("/")
            if request.headers.get("Sec-Fetch-Site") == "cross-site" or (origin and origin not in (public_origin, local_origin)):
                abort(403)
            if request.method == "POST":
                if not budget.take():
                    abort(429)
                if not request.is_json:
                    abort(415)
                try:
                    valid = valid_callback(request.get_json())
                except (TypeError, ValueError, KeyError, RecursionError):
                    valid = False
                if not valid:
                    abort(400)
        elif path not in {"/", "/healthz", "/_dash-layout", "/_dash-dependencies", "/_favicon.ico"} | assets and not path.startswith("/_dash-component-suites/"):
            abort(404)
        # Ordinary clock/graph callbacks must not compete for geometry slots.
        # A short bounded wait absorbs a normal burst of simultaneous visitors.
        heavy_callback = (path == "/_dash-update-component" and request.method == "POST"
                          and "home-scene.children" in request.get_json().get("output", ""))
        if path == "/_dash-layout" or heavy_callback:
            semaphore = layouts if path == "/_dash-layout" else work
            if not semaphore.acquire(timeout=2):
                abort(503)
            g.simulation_work = semaphore

    @server.teardown_request
    def release(_error):
        semaphore = g.pop("simulation_work", None)
        if semaphore is not None:
            semaphore.release()

    @server.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = json.dumps({"error": error.name, "status": error.code})
        response.content_type = "application/json"
        if error.code in (429, 503):
            response.headers["Retry-After"] = "3"
        return response

    @server.after_request
    def headers(response):
        response.headers.update({"Content-Security-Policy": csp, "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()"})
        if public_host and request.environ.get("HTTP_HOST", "").split(":")[0] == public_host:
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.path in ("/", "/healthz", "/_dash-layout", "/_dash-dependencies", "/_dash-update-component") or response.status_code >= 400:
            response.headers["Cache-Control"] = "no-store"
        return response

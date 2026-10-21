"""Small public smoke check; no credentials, load test or persistent monitor.

Run: python scripts/check_site.py
Use --url http://127.0.0.1:8050 for a locally running copy.
"""
import argparse
from datetime import datetime, timezone
import json
from time import perf_counter
from urllib.parse import urlsplit

import requests


def check(base, timeout):
    session = requests.Session()
    result = {"url": base, "checked_utc": datetime.now(timezone.utc).isoformat(), "checks": []}
    for path in ("/healthz", "/", "/_dash-dependencies", "/assets/style.css"):
        start = perf_counter()
        response = session.get(base + path, timeout=timeout)
        response.raise_for_status()
        result["checks"].append({"path": path, "status": response.status_code,
                                  "seconds": round(perf_counter() - start, 3)})
        if path == "/healthz":
            health = response.json()
            if health.get("status") != "ok" or health.get("application") != "smart":
                raise ValueError("Unexpected health response")
            result["release"] = health.get("release", "legacy")
        elif path == "/_dash-dependencies":
            callbacks = response.json()
        if response.headers.get("X-Content-Type-Options") != "nosniff":
            raise ValueError("Expected security headers are missing")
    callback = next(item for item in callbacks if "thermostat-value.children" in item["output"])
    # A complete scenario is required by the server's input schema.
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from energy import DEFAULT
    start = perf_counter()
    response = session.post(base + "/_dash-update-component", timeout=timeout,
        headers={"Origin": base}, json={"output": callback["output"],
        "outputs": [{"id": cid, "property": prop} for cid, prop in
                    (("thermostat-value", "children"), ("climate-chart", "figure"),
                     ("climate-load", "figure"), ("climate-summary", "children"))],
        "inputs": [{"id": "scenario", "property": "data", "value": DEFAULT},
                   {"id": "effective-index", "property": "data", "value": 57}],
        "state": [], "changedPropIds": ["scenario.data"]})
    response.raise_for_status()
    if response.json()["response"]["thermostat-value"]["children"] != "21":
        raise ValueError("The thermostat callback did not produce its expected result")
    result["checks"].append({"path": "/_dash-update-component", "status": response.status_code,
                              "seconds": round(perf_counter() - start, 3)})
    result["healthy"] = True
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="https://behnamproject-smarthome.onrender.com")
    parser.add_argument("--timeout", type=int, default=90, help="Allow a free instance time to wake")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")):
        parser.error("Use HTTPS, or HTTP on localhost")
    try:
        print(json.dumps(check(base, min(120, max(1, args.timeout))), indent=2))
    except (requests.RequestException, ValueError, KeyError, StopIteration) as error:
        print(json.dumps({"healthy": False, "error": type(error).__name__,
                          "message": "Check failed. Inspect Render events/logs and retry after the service has started."}))
        raise SystemExit(1)

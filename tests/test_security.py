"""Security checks exercise rejected HTTP requests and legitimate controls."""
from copy import deepcopy
import json

import pytest

from app import app, server
from energy import DEFAULT
from runtime import step
from security import MAX_BODY, RequestBudget


def climate_payload():
    key = next(key for key in app.callback_map if "thermostat-value.children" in key)
    metadata = app.callback_map[key]
    return {"output": key, "outputs": [{"id": item.component_id, "property": item.component_property} for item in metadata["output"]],
            "inputs": [{"id": "scenario", "property": "data", "value": deepcopy(DEFAULT)},
                       {"id": "effective-index", "property": "data", "value": 57}],
            "state": [], "changedPropIds": ["scenario.data"]}


def test_security_headers_and_private_paths():
    client = server.test_client()
    for path in ("/", "/healthz", "/assets/style.css", "/.env", "/.git/config", "/app.py", "/assets/CON.txt.html"):
        response = client.get(path)
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        csp = response.headers["Content-Security-Policy"]
        assert "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
        assert "script-src 'self' 'sha256-" in csp
        if path in ("/", "/healthz"):
            assert response.headers["Cache-Control"] == "no-store"
        if path.startswith("/.") or path in ("/app.py", "/assets/CON.txt.html"):
            assert response.status_code == 404
    assert client.get("/", headers={"Host": "attacker.invalid"}).status_code == 400


def test_no_cross_site_control_requests_but_normal_browser_allowed():
    client = server.test_client()
    for headers in ({"Origin": "https://attacker.invalid"}, {"Sec-Fetch-Site": "cross-site"}, {"Origin": "null"}):
        assert client.post("/_dash-update-component", json=climate_payload(), headers=headers).status_code == 403
    assert client.post("/_dash-update-component", json=climate_payload(), headers={"Origin": "http://localhost"}).status_code == 200
    assert client.post("/_dash-update-component", data="anything", content_type="text/plain").status_code == 415


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(output="unregistered.callback"),
    lambda p: p["inputs"][0].update(id="different-store"),
    lambda p: p["inputs"][1].update(value="not-a-number"),
    lambda p: p["inputs"][1].update(value=float("nan")),
    lambda p: p["inputs"][0].update(value={}),
    lambda p: p["outputs"][0].update(id="unexpected-output"),
    lambda p: p.update(changedPropIds=["unregistered.data"]),
])
def test_malformed_callbacks_return_400_without_running_model(mutation):
    payload = climate_payload()
    mutation(payload)
    response = server.test_client().post("/_dash-update-component", json=payload)
    assert response.status_code == 400
    assert "Traceback" not in response.get_data(as_text=True)


def test_body_and_complexity_limits_do_not_disable_health():
    client = server.test_client()
    assert client.post("/_dash-update-component", data=" " * (MAX_BODY + 1), content_type="application/json").status_code == 413
    response = client.post("/_dash-update-component", data='[' * 1200 + ']' * 1200, content_type="application/json")
    assert response.status_code == 400
    assert client.get("/healthz").get_json()["status"] == "ok"


def test_live_store_requires_complete_finite_snapshot():
    key = next(key for key in app.callback_map if "dr-event-status.children" in key)
    metadata = app.callback_map[key]
    payload = {"output": key, "outputs": [{"id": item.component_id, "property": item.component_property} for item in metadata["output"]],
        "inputs": [{**metadata["inputs"][0], "value": DEFAULT}, {**metadata["inputs"][1], "value": step(DEFAULT)}],
        "state": [], "changedPropIds": ["live-state.data"]}
    assert server.test_client().post("/_dash-update-component", json=payload).status_code == 200
    payload["inputs"][1]["value"]["temperatures"] = []
    assert server.test_client().post("/_dash-update-component", json=payload).status_code == 400


def test_overload_is_bounded_and_health_remains_available(monkeypatch):
    guard = server.extensions["simulation_guard"]
    monkeypatch.setattr(guard["budget"], "take", lambda: False)
    client = server.test_client()
    response = client.post("/_dash-update-component", json=climate_payload())
    assert response.status_code == 429 and response.headers["Retry-After"] == "3"
    assert client.get("/healthz").status_code == 200
    assert guard["layouts"].acquire(blocking=False)
    assert guard["layouts"].acquire(blocking=False)
    try:
        assert client.get("/_dash-layout").status_code == 503
        assert client.get("/healthz").status_code == 200
    finally:
        guard["layouts"].release()
        guard["layouts"].release()


def test_budget_refills_without_unbounded_client_tracking(monkeypatch):
    import security
    clock = [100.0]
    monkeypatch.setattr(security, "monotonic", lambda: clock[0])
    budget = RequestBudget(capacity=2, refill=1)
    assert budget.take() and budget.take() and not budget.take()
    clock[0] += 1
    assert budget.take() and not budget.take()

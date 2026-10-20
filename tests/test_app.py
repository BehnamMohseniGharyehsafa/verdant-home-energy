"""HTTP and callback integration tests for every dashboard view."""
import json
from app import app, server, build_overview, render_devices, render_climate, render_flex, render_analytics, navigate
from energy import DEFAULT, DEVICES, ROOMS


def test_http_routes_and_callback_registration():
    client = server.test_client()
    for path in ["/", "/healthz", "/_dash-layout", "/_dash-dependencies", "/assets/style.css"]:
        response = client.get(path)
        assert response.status_code == 200, path
    layout = client.get("/_dash-layout").get_json()
    ids = []
    def walk(node):
        if isinstance(node, dict):
            if "props" in node and "id" in node["props"]:
                ids.append(json.dumps(node["props"]["id"], sort_keys=True))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(layout)
    assert len(ids) == len(set(ids)), "Duplicate component IDs"
    assert any("live-state.data" in key for key in app.callback_map)
    assert any("home-scene.children" in key for key in app.callback_map)


def test_all_views_render_with_changed_scenario():
    state = json.loads(json.dumps(DEFAULT))
    state.update(dr=True, optimize=True, temperature=19, solar=False)
    state["devices"]["ev"] = True
    result = build_overview(state, 72)
    assert len(result) == 5
    assert len(result[1].data) == 3
    device_ids = [{"type": "device-status", "device": d} for d in DEVICES]
    room_ids = [{"type": "brightness-label", "room": r} for r in ROOMS]
    assert len(render_devices(state, 72, device_ids, room_ids)[0]) == len(DEVICES)
    assert len(render_climate(state, 72)) == 4
    assert len(render_flex(state)) == 5
    assert len(render_analytics(state, 30)) == 6
    assert navigate("climate")[2] == "page"


def test_real_dash_callback_http():
    client = server.test_client()
    callback = next(key for key in app.callback_map if "thermostat-value.children" in key)
    outputs = [{"id": item.component_id, "property": item.component_property}
               for item in app.callback_map[callback]["output"]]
    response = client.post("/_dash-update-component", json={
        "output": callback, "outputs": outputs,
        "inputs": [{"id": "scenario", "property": "data", "value": DEFAULT},
                   {"id": "effective-index", "property": "data", "value": 57}],
        "state": [], "changedPropIds": ["scenario.data"]})
    assert response.status_code == 200
    assert response.get_json()["response"]["thermostat-value"]["children"] == "21"

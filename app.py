"""Verdant: a Python-authored Smart Home Energy Management demonstrator.

Run: python app.py. Production: gunicorn app:server --bind 0.0.0.0:$PORT
"""
from datetime import date
import csv
import io
import json
import os

import numpy as np
from dash import Dash, Input, Output, State, ALL, dcc, html, no_update
from dash.exceptions import PreventUpdate

import charts
from energy import (DEFAULT, DEVICES, ROOMS, HOURS, DT, default_state, evaluate_state,
                    history, sanitize, time_label, room_power)
from house import house_figure
from ui import layout, icon, metric, card, pill

DEMO_DATE = date.fromisoformat(os.getenv("DEMO_DATE", "2026-10-20"))
PAGES = ["overview", "devices", "climate", "analytics", "flexibility", "settings"]
PAGE_TITLES = ["Overview", "Devices & lighting", "Heating & cooling", "Energy analytics",
               "Demand response", "System & assumptions"]

app = Dash(__name__, title="Verdant · Home Energy", update_title=None,
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"},
                      {"name": "description", "content": "An interactive Python smart-home energy management demonstration with a 3D home, device controls, solar, storage and transparent analytics."}])
server = app.server
app.layout = lambda: layout(DEMO_DATE)


@server.get("/healthz")
def health():
    return {"status": "ok", "mode": "simulation", "application": "verdant"}, 200


@app.callback([Output("page-" + page, "className") for page in PAGES] + [Output("page-title", "children")],
              Input("navigation", "value"))
def navigate(page):
    page = page if page in PAGES else "overview"
    return ["page" if p == page else "page hidden" for p in PAGES] + [PAGE_TITLES[PAGES.index(page)]]


@app.callback(Output({"type": "brightness", "room": ALL}, "value"),
              Output("thermostat", "value"), Output("hvac-mode", "value"),
              Input("scene", "value"), State({"type": "brightness", "room": ALL}, "id"),
              prevent_initial_call=True)
def apply_scene(scene, light_ids):
    scenes = {"Home": (65, 21), "Eco": (35, 19), "Away": (0, 16)}
    brightness, target = scenes.get(scene, scenes["Home"])
    return [brightness for _ in light_ids], target, "heat"


@app.callback(Output("scenario", "data"),
    Input({"type": "brightness", "room": ALL}, "value"),
    Input({"type": "device-toggle", "device": ALL}, "value"),
    Input("thermostat", "value"), Input("hvac-mode", "value"),
    Input("solar-toggle", "value"), Input("battery-toggle", "value"),
    Input("optimizer-toggle", "value"), Input("dr-toggle", "value"),
    *[Input("setting-" + key, "value") for key in ("offpeak", "day", "peak", "export_rate", "standing", "carbon")],
    State({"type": "brightness", "room": ALL}, "id"),
    State({"type": "device-toggle", "device": ALL}, "id"))
def update_state(brightness, devices, temperature, hvac, solar, battery, optimize, dr,
                 offpeak, day_rate, peak, export_rate, standing, carbon, light_ids, device_ids):
    state = default_state()
    state["lights"] = {key["room"]: value for key, value in zip(light_ids, brightness)}
    state["devices"] = {key["device"]: "on" in (value or []) for key, value in zip(device_ids, devices)}
    state.update(temperature=temperature, hvac=hvac, solar="on" in (solar or []),
                 battery="on" in (battery or []), optimize="on" in (optimize or []), dr="on" in (dr or []),
                 offpeak=offpeak, day=day_rate, peak=peak, export_rate=export_rate, standing=standing, carbon=carbon)
    return sanitize(state)


@app.callback(Output("selected-room", "value"), Input("house-view", "clickData"), prevent_initial_call=True)
def select_room(click):
    if not click:
        raise PreventUpdate
    room = click.get("points", [{}])[0].get("customdata")
    return room if isinstance(room, str) and room in ROOMS else no_update


def stat(value, label, unit=""):
    return html.Div([html.Strong([value, html.Small(" " + unit) if unit else None]), html.Span(label)], className="small-stat")


def insight(symbol, title, text, tag):
    return card([html.Div([icon(symbol, 22, "#c4f286"), pill(tag, "muted")], className="insight-top"),
                 html.H3(title), html.P(text)], "insight-card")


def build_overview(state, index, room, layer):
    day, reference, event = evaluate_state(state)
    a, b = day.totals, reference.totals
    demand_change = b["load"] - a["load"]
    cost_change = b["cost"] - a["cost"]
    carbon_change = b["carbon"] - a["carbon"]
    delta_label = lambda val, unit: f"{abs(val):.2f} {unit} {'below' if val >= 0 else 'above'} reference"
    metrics = [
        metric("Home energy demand", f"{a['load']:.1f}", "kWh", delta_label(demand_change, "kWh"), "bolt", day.load),
        metric("Projected electricity cost", f"€{a['cost']:.2f}", "/ day", delta_label(cost_change, "€"), "wallet", np.cumsum(day.interval_cost), "amber"),
        metric("Solar self-consumption", f"{a['solar_self_consumption']:.0f}", "%", f"{a['solar']:.1f} kWh solar generated", "sun", day.pv, "cyan"),
        metric("Operational carbon avoided", f"{carbon_change:.2f}", "kg CO₂e", "Against declared daily reference", "leaf", reference.grid_in - day.grid_in, "blue"),
    ]
    soc = day.soc[index] / 10 * 100
    flow_stats = [stat(f"{day.pv[index]:.2f}", "Solar", "kW"),
                  stat(f"{day.grid_in[index]:.2f}", "Import", "kW"),
                  stat(f"{soc:.0f}%" if state["battery"] else "Off", "Battery charge")]
    info = ROOMS[room]
    power = room_power(day, room, index)
    active_devices = [device["name"] for key, device in DEVICES.items()
                      if device["room"] == room and day.schedules[key]["power"][index] > 0]
    detail = [html.Div([html.Span("SELECTED ROOM", className="eyebrow"), icon("home", 17)], className="inline spread"),
        html.H3(info["name"]),
        html.Div([html.Strong(f"{power * 1000:.0f}"), html.Span("W allocated demand")], className="room-power"),
        html.Div([pill(f"{state['lights'][room]:.0f}% lighting", "amber"),
                  pill(f"{state['temperature']:.1f}°C target" if state["hvac"] != "off" else "HVAC off", "muted")], className="room-pills"),
        html.P("Operating: " + ", ".join(active_devices) if active_devices else "No scheduled appliance operating in this interval.", className="subtle"),
        html.Small(f"{info['area']:.1f} m² · HVAC and always-on power allocated by floor area", className="footnote")]
    tariff_name = "Off-peak" if index < 28 else ("Peak" if 68 <= index < 76 else "Day rate")
    current_price = [html.Strong(f"{day.prices[index] * 100:.0f}"), html.Span("c / kWh"), pill(tariff_name.upper(), "amber")]
    optimized, _, _ = evaluate_state(dict(state, optimize=True))
    opportunity = a["cost"] - optimized.totals["cost"]
    if not state["optimize"] and opportunity > .005:
        first = insight("moon", "Put your tariff to work", f"Cheapest-tariff scheduling could reduce this scenario's daily net cost by €{opportunity:.2f}. Explore Devices & lighting.", "SMART SCHEDULING")
    elif state["optimize"]:
        first = insight("check", "Your schedule is tariff-aware", "Flexible daily cycles are scheduled at the lowest import-tariff cost. Inspect the operating windows in Devices & lighting.", "SCHEDULING ENABLED")
    else:
        first = insight("sun", "Timing is about more than tariffs", "Cheapest-tariff scheduling does not lower this scenario's net cost. Solar self-consumption and battery dispatch also affect your bill.", "SCENARIO INSIGHT")
    recommendations = [first,
        insight("battery", "Follow your stored energy", f"Battery ends the model day at {day.soc[-1]:.2f} kWh" + (f", from {day.soc[0]:.2f} kWh initially stored. Daily cost benefits include that initial energy." if state["battery"] else ". Enable storage in System to explore self-consumption."), "STORAGE INSIGHT"),
        insight("flex", "Make room for flexibility", f"{'Participation enabled' if state['dr'] else 'Try the demand-response simulator'}: shift flexible loads away from 17:00–19:00 and inspect the matched import reduction.", "EVENING PEAK")]
    return (metrics, house_figure(day, index, room, layer), charts.flow(day, index), flow_stats,
            detail, charts.profile(day, index), charts.price(day, index), current_price,
            recommendations, f"{day.outdoor[index]:.1f}°C", time_label(index))


@app.callback(
    Output("overview-metrics", "children"), Output("house-view", "figure"),
    Output("flow-chart", "figure"), Output("flow-stats", "children"), Output("room-detail", "children"),
    Output("daily-chart", "figure"), Output("price-chart", "figure"), Output("price-current", "children"),
    Output("recommendations", "children"), Output("weather-label", "children"), Output("time-value", "children"),
    Input("scenario", "data"), Input("simulation-time", "value"), Input("selected-room", "value"), Input("house-layer", "value"))
def render_overview(raw, index, room, layer):
    state = sanitize(raw)
    index = max(0, min(95, int(index or 0)))
    room = room if room in ROOMS else "living"
    return build_overview(state, index, room, layer)


@app.callback(Output({"type": "device-status", "device": ALL}, "children"),
    Output({"type": "brightness-label", "room": ALL}, "children"), Output("schedule-chart", "figure"),
    Input("scenario", "data"), Input("simulation-time", "value"),
    State({"type": "device-status", "device": ALL}, "id"),
    State({"type": "brightness-label", "room": ALL}, "id"))
def render_devices(raw, index, device_ids, room_ids):
    state = sanitize(raw)
    day, _, _ = evaluate_state(state)
    index = max(0, min(95, int(index or 0)))
    statuses = []
    for item in device_ids:
        key = item["device"]
        device = day.schedules[key]
        if not state["devices"][key]:
            statuses.append([pill("DISABLED", "muted"), html.Span("0.00 kWh / day")])
        else:
            active = device["power"][index] > 0
            statuses.append([pill("OPERATING" if active else "SCHEDULED", "green" if active else "blue"),
                            html.Span(f"{time_label(device['start'])}–{time_label(device['end'])}")])
    return statuses, [f"{state['lights'][item['room']]:.0f}%" for item in room_ids], charts.schedule(day)


@app.callback(Output("thermostat-value", "children"), Output("climate-chart", "figure"),
              Output("climate-load", "figure"), Output("climate-summary", "children"),
              Input("scenario", "data"), Input("simulation-time", "value"))
def render_climate(raw, index):
    state = sanitize(raw)
    day, _, _ = evaluate_state(state)
    index = max(0, min(95, int(index or 0)))
    stats = [stat(f"{day.loads['Heating & cooling'].sum() * DT:.2f}", "HVAC / day", "kWh"),
             stat(f"{day.loads['Heating & cooling'][index] * 1000:.0f}", "Selected interval", "W"),
             stat({"heat": "Heating", "cool": "Cooling", "off": "Off"}[state["hvac"]], "Operating mode")]
    return f"{state['temperature']:g}", charts.climate(day, index), charts.climate_load(day), stats


@app.callback(Output("dr-chart", "figure"), Output("dr-metrics", "children"), Input("scenario", "data"))
def render_flex(raw):
    state = sanitize(raw)
    day, _, event = evaluate_state(state)
    cards = [
        card([html.Span("MODELLED EVENT REDUCTION", className="eyebrow"), html.Div([html.Strong(f"{event['reduction']:.2f}"), html.Span("kWh")], className="metric-value"), html.P("Net grid import reduction over 17:00–19:00", className="subtle")]),
        card([html.Span("ILLUSTRATIVE REWARD", className="eyebrow"), html.Div([html.Strong(f"€{event['reward']:.2f}")], className="metric-value"), html.P("€0.35 × modelled event reduction · no real payment", className="subtle")]),
        card([html.Span("PARTICIPATION", className="eyebrow"), html.Div([html.Strong("Enabled" if state["dr"] else "Available")], className="metric-value smaller"), html.P("Changes apply to the replayed scenario day", className="subtle")])]
    return charts.demand_response(day, event), cards


@app.callback(Output("analytics-metrics", "children"), Output("cost-comparison", "figure"),
    Output("breakdown-chart", "figure"), Output("load-comparison", "figure"),
    Output("carbon-comparison", "figure"), Output("scenario-ledger", "children"),
    Input("scenario", "data"), Input("analytics-range", "value"))
def render_analytics(raw, count):
    state = sanitize(raw)
    count = 30 if count == 30 else 7
    rows = history(state, count, DEMO_DATE)
    totals = {key: sum(row[key] for row in rows) for key in rows[0] if key != "date"}
    demand_saving = totals["reference_load"] - totals["load"]
    carbon_saving = totals["reference_carbon"] - totals["carbon"]
    metrics = [
        metric("Scenario demand", f"{totals['load']:.1f}", "kWh", f"{count}-day synthetic replay", "bolt", [r["load"] for r in rows]),
        metric("Net financial saving", f"€{totals['saving']:.2f}", "", "Reference − scenario + flex reward", "wallet", [r["saving"] for r in rows], "amber"),
        metric("Demand reduction", f"{demand_saving:.1f}", "kWh", "Against declared reference", "chart", [r["reference_load"] - r["load"] for r in rows], "cyan"),
        metric("Operational carbon avoided", f"{carbon_saving:.2f}", "kg CO₂e", f"Assumed factor: {state['carbon']:.2f} kg/kWh", "leaf", [r["reference_carbon"] - r["carbon"] for r in rows], "blue")]
    headers = ["Model day", "Demand", "Import", "Export", "Net cost", "Flex reward", "Net saving", "CO₂e"]
    body = [html.Tr([html.Td(row["date"]), html.Td(f"{row['load']:.2f} kWh"),
                    html.Td(f"{row['import']:.2f} kWh"), html.Td(f"{row['export']:.2f} kWh"),
                    html.Td(f"€{row['cost']:.2f}"), html.Td(f"€{row['reward']:.2f}"),
                    html.Td(f"€{row['saving']:.2f}", className="positive" if row["saving"] >= 0 else "negative"),
                    html.Td(f"{row['carbon']:.2f} kg")]) for row in rows]
    table = html.Table([html.Thead(html.Tr([html.Th(h) for h in headers])), html.Tbody(body)], className="ledger")
    day, _, _ = evaluate_state(state)
    return metrics, charts.comparison(rows), charts.breakdown(day), charts.comparison(rows, "load"), charts.comparison(rows, "carbon"), table


def export_csv(raw):
    state = sanitize(raw)
    day, reference, event = evaluate_state(state)
    columns = ["model_date", "time", "interval_hours", "home_kw", "solar_kw", "battery_charge_kw",
               "battery_discharge_kw", "battery_soc_start_kwh", "battery_soc_end_kwh", "grid_import_kw", "grid_export_kw",
               "import_eur_per_kwh", "export_eur_per_kwh", "standing_charge_eur", "net_cost_eur",
               "carbon_kg_co2e", "reference_home_kw", "reference_import_kw", "reference_export_kw",
               "reference_net_cost_eur", "flex_reward_eur", "grid_carbon_kg_per_kwh", "mode"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for i in range(96):
        standing = state["standing"] if i == 0 else 0
        row = [DEMO_DATE.isoformat(), time_label(i), DT, day.load[i], day.pv[i], day.charge[i],
               day.discharge[i], day.soc[i], day.soc[i + 1], day.grid_in[i], day.grid_out[i],
               day.prices[i], state["export_rate"], standing, day.interval_cost[i] + standing,
               day.grid_in[i] * DT * state["carbon"], reference.load[i], reference.grid_in[i], reference.grid_out[i],
               reference.interval_cost[i] + standing, event["reward"] if i == 0 else 0, state["carbon"], "SIMULATED"]
        writer.writerow({key: round(float(value), 8) if isinstance(value, (float, np.floating)) else value
                         for key, value in zip(columns, row)})
    return stream.getvalue()


@app.callback(Output("download-data", "data"), Input("export-button", "n_clicks"),
              State("scenario", "data"), prevent_initial_call=True)
def download(n_clicks, raw):
    if not n_clicks:
        raise PreventUpdate
    return dcc.send_string(export_csv(raw), f"verdant-simulated-{DEMO_DATE.isoformat()}.csv")


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8050")), debug=False)

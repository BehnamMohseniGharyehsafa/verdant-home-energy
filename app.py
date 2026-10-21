"""Smart: a Python-authored Smart Home Energy Management demonstrator.

Run: python app.py. Production: gunicorn app:server --bind 0.0.0.0:$PORT
"""
from datetime import date, datetime, timezone
from urllib.parse import quote
import math
import csv
import io
import json
import os

import numpy as np
from dash import Dash, Input, Output, State, ALL, dcc, html, no_update, ctx
from dash.exceptions import PreventUpdate
from dash import _dash_renderer

# dash-vtk's published renderer targets React 16. Pin its supported runtime.
_dash_renderer._set_react_version("16.14.0")

import charts
from energy import (DEFAULT, DEVICES, ROOMS, HOURS, DT, default_state, evaluate_state,
                    history, sanitize, time_label, room_power)
from house_scene import scene_children, scene_patch, CAMERAS
from runtime import step, irish_now, picked_object, control_state
from flexibility import report as flex_report, network_snapshot
from ui import layout, icon, metric, card, pill

DEMO_DATE = date.fromisoformat(os.getenv("DEMO_DATE", "2026-10-20"))
PAGES = ["overview", "devices", "climate", "analytics", "flexibility", "settings"]
PAGE_TITLES = ["Overview", "Devices & lighting", "Heating & cooling", "Energy analytics",
               "Demand response", "System & assumptions"]

app = Dash(__name__, title="Smart · Home Energy", update_title=None,
           meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"},
                      {"name": "description", "content": "An interactive Python smart-home energy management demonstration with a 3D home, device controls, solar, storage and transparent analytics."}])
server = app.server
# This tree contains only initial values; each visitor's live state stays in
# browser-memory stores. A callable layout makes Dash embed a second, 11 MB
# validation copy of the 3D meshes in every HTML response (including HEAD).
# A fixed tree keeps validation enabled and sends geometry only via the layout.
app.layout = layout(DEMO_DATE)


@server.get("/healthz")
def health():
    return {"status": "ok", "mode": "simulation", "application": "smart",
            "release": "2026.10.21-security.1"}, 200


@app.callback([Output("page-" + page, "className") for page in PAGES] + [Output("page-title", "children")],
              Input("navigation", "value"))
def navigate(page):
    page = page if page in PAGES else "overview"
    return ["page" if p == page else "page hidden" for p in PAGES] + [PAGE_TITLES[PAGES.index(page)]]


@app.callback(Output({"type": "brightness", "room": ALL}, "value"),
              Output("thermostat", "value"), Output("hvac-mode", "value"),
              Output("device-overrides","data"),Output("control-feedback","children"),
              Output("home-scene","clickInfo"),Output("devices-scene","clickInfo"),
              Input("scene", "value"),Input("home-scene","clickInfo"),Input("devices-scene","clickInfo"),
              Input({"type":"room-switch","room":ALL},"n_clicks"),
              Input({"type":"live-device","device":ALL},"n_clicks"),Input("reset-overrides","n_clicks"),
              State({"type": "brightness", "room": ALL}, "id"),
              State({"type":"brightness","room":ALL},"value"),
              State("device-overrides","data"),State("live-state","data"),
              prevent_initial_call=True)
def apply_controls(scene, home_pick, devices_pick, room_clicks, device_clicks, reset_clicks,
                   light_ids, levels, overrides, live):
    trigger=ctx.triggered_id
    overrides=dict(overrides or {})
    live=live or {}
    untouched=no_update
    untouched_levels=[no_update for _ in light_ids]
    clear_home=clear_devices=no_update
    if trigger=="scene":
        scenes={"Home":(65,21),"Eco":(35,19),"Away":(0,16)}
        brightness,target=scenes.get(scene,scenes["Home"])
        return [brightness for _ in light_ids],target,"heat",untouched,f"{scene} scene applied.",untouched,untouched
    if trigger=="reset-overrides":
        return untouched_levels,untouched,untouched,{},"Automatic appliance schedules restored.",untouched,untouched
    if isinstance(trigger,dict):
        picked=("light",trigger["room"]) if trigger.get("type")=="room-switch" else ("device",trigger.get("device"))
    elif trigger in ("home-scene","devices-scene"):
        picked=picked_object(home_pick if trigger=="home-scene" else devices_pick)
        clear_home=clear_devices=None
    else:
        raise PreventUpdate
    if not picked or picked[0] not in ("light","device"):
        raise PreventUpdate
    kind,key=picked
    if kind=="light" and key in ROOMS:
        values=dict(zip([item["room"] for item in light_ids],levels))
        remembered=dict(overrides.get("_light_levels",{}))
        current=float(values.get(key,65) or 0)
        if current>0:
            remembered[key]=current
            values[key]=0
        else:
            values[key]=remembered.get(key,65)
        overrides["_light_levels"]=remembered
        message=f"{ROOMS[key]['name']} lighting {'off' if values[key]==0 else 'on'} · {values[key]:g}% brightness."
        return [values[item["room"]] for item in light_ids],untouched,untouched,overrides,message,clear_home,clear_devices
    if kind=="device" and key in DEVICES:
        was_on=float(live.get("appliances",{}).get(key,0))>.001
        overrides[key]="off" if was_on else "on"
        message=f"{DEVICES[key]['name']}: live manual {overrides[key].upper()}. Daily schedule projection is unchanged."
        return untouched_levels,untouched,untouched,overrides,message,clear_home,clear_devices
    raise PreventUpdate


def apply_scene(scene, light_ids):
    """Pure scene helper retained for callers and independent tests."""
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
    Input("dr-dim","value"),Input("dr-relief","value"),Input("dr-shift","value"),Input("dr-reward","value"),
    State({"type": "brightness", "room": ALL}, "id"),
    State({"type": "device-toggle", "device": ALL}, "id"))
def update_state(brightness, devices, temperature, hvac, solar, battery, optimize, dr,
                 offpeak, day_rate, peak, export_rate, standing, carbon, dr_dim,dr_relief,dr_shift,dr_reward,light_ids, device_ids):
    state = default_state()
    state["lights"] = {key["room"]: value for key, value in zip(light_ids, brightness)}
    state["devices"] = {key["device"]: "on" in (value or []) for key, value in zip(device_ids, devices)}
    state.update(temperature=temperature, hvac=hvac, solar="on" in (solar or []),
                 battery="on" in (battery or []), optimize="on" in (optimize or []), dr="on" in (dr or []),
                 offpeak=offpeak, day=day_rate, peak=peak, export_rate=export_rate, standing=standing, carbon=carbon,
                 dr_dim=dr_dim,dr_relief=dr_relief,dr_shift="on" in (dr_shift or []),dr_reward=dr_reward)
    return sanitize(state)


@app.callback(Output("selected-room", "value"), Input("home-scene", "clickInfo"),
              Input("devices-scene","clickInfo"), prevent_initial_call=True)
def select_room(home_click, devices_click=None):
    click=devices_click if ctx.triggered_id=="devices-scene" else home_click
    picked=picked_object(click)
    if not picked:
        raise PreventUpdate
    kind,key=picked
    return key if kind in ("light","room") else DEVICES[key]["room"]


def stat(value, label, unit=""):
    return html.Div([html.Strong([value, html.Small(" " + unit) if unit else None]), html.Span(label)], className="small-stat")


def insight(symbol, title, text, tag):
    return card([html.Div([icon(symbol, 22, "#c4f286"), pill(tag, "muted")], className="insight-top"),
                 html.H3(title), html.P(text)], "insight-card")


def build_overview(state, index):
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
    return metrics, charts.profile(day,index), charts.price(day,index), current_price,recommendations


@app.callback(
    Output("overview-metrics", "children"),
    Output("daily-chart", "figure"), Output("price-chart", "figure"), Output("price-current", "children"),
    Output("recommendations", "children"),
    Input("scenario", "data"), Input("effective-index", "data"))
def render_overview(raw, index):
    state = sanitize(raw)
    index = max(0, min(95, int(index or 0)))
    return build_overview(state,index)


@app.callback(Output({"type": "device-status", "device": ALL}, "children"),
    Output({"type": "brightness-label", "room": ALL}, "children"), Output("schedule-chart", "figure"),
    Input("scenario", "data"), Input("effective-index", "data"),
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
              Input("scenario", "data"), Input("effective-index", "data"))
def render_climate(raw, index):
    state = sanitize(raw)
    day, _, _ = evaluate_state(state)
    index = max(0, min(95, int(index or 0)))
    stats = [stat(f"{day.loads['Heating & cooling'].sum() * DT:.2f}", "HVAC / day", "kWh"),
             stat(f"{day.loads['Heating & cooling'][index] * 1000:.0f}", "Selected interval", "W"),
             stat({"heat": "Heating", "cool": "Cooling", "off": "Off"}[state["hvac"]], "Operating mode")]
    return f"{state['temperature']:g}", charts.climate(day, index), charts.climate_load(day), stats


@app.callback(Output("dr-chart", "figure"), Output("dr-metrics", "children"),
              Output("dr-impact-chart","figure"),Output("dr-plan","children"),Output("dr-explanation","children"),
              Input("scenario", "data"))
def render_flex(raw):
    result=flex_report(raw)
    state,day,event=result["state"],result["day"],result["event"]
    cards = [
        metric("Import without response",f"{result['before_kwh']:.2f}","kWh","Matched 17:00–19:00 baseline","grid",result["baseline"].grid_in[68:76],"blue"),
        metric("Import with your settings",f"{result['after_kwh']:.2f}","kWh","Same event window and assets","home",day.grid_in[68:76]),
        card([html.Span("MODELLED EVENT REDUCTION", className="eyebrow"), html.Div([html.Strong(f"{event['reduction']:.2f}"), html.Span("kWh")], className="metric-value"), html.P("Net grid import reduction over 17:00–19:00", className="subtle")]),
        card([html.Span("ILLUSTRATIVE REWARD", className="eyebrow"), html.Div([html.Strong(f"€{event['reward']:.2f}")], className="metric-value"), html.P(f"€{state['dr_reward']:.2f}/kWh × reduction · no real payment", className="subtle")])]
    rows=[]
    for row in result["rows"]:
        status="Disabled" if not row["enabled"] else ("Shifted" if row["shifted"] else ("Unchanged" if row["flexible"] else "Fixed window"))
        rows.append(html.Tr([html.Td(row["name"]),html.Td(row["before"] if row["enabled"] else "N/A"),
            html.Td(row["after"] if row["enabled"] else "N/A"),html.Td(f"{row['energy']:.2f} kWh"),
            html.Td(f"{row['event_delta']:+.2f} kWh"),html.Td(pill(status,"green" if row["shifted"] else "muted"))]))
    table=html.Table([html.Thead(html.Tr([html.Th(text) for text in
        ("Appliance","Without response","Your settings","Cycle energy","Event load avoided","Action")])),html.Tbody(rows)],className="ledger")
    explanation=[html.Div([html.Strong(f"{result['before_peak']:.2f} → {result['after_peak']:.2f} kW"),html.Span("Peak import in event")]),
        html.Div([html.Strong(f"€{result['bill_delta']:+.2f}"),html.Span("Whole-day bill benefit · excludes reward")]),
        html.Div([html.Strong(f"{result['event_carbon_delta']:+.2f} kg"),html.Span("Event import carbon avoided")]),
        html.P(f"Your strategy: {'shift flexible loads' if state['dr_shift'] else 'keep appliance windows'}; reduce lighting power by {state['dr_dim']:g}%; relax heating/cooling by {state['dr_relief']:g}°C. "
            +("Participation is enabled." if state["dr"] else "Participation is off, so the comparison currently shows no response.")
            +" Storage interaction captures the change in battery dispatch and export; negative contributions are retained.",className="footnote")]
    return charts.demand_response(day,event),cards,charts.flex_impacts(result),table,explanation


@app.callback(Output("dr-event-status","children"),Output("dr-now","children"),
              Input("scenario","data"),Input("live-state","data"))
def render_flex_now(raw,live):
    live=live or {}
    result=flex_report(raw,live.get("index",70))
    state=result["state"]; seconds=int(live.get("seconds",17.5*3600)); i=result["index"]
    active=17*3600<=seconds<19*3600
    stage="Event active" if active else ("Event upcoming" if seconds<17*3600 else "Event complete")
    until=(19*3600-seconds) if active else ((17*3600-seconds)%86400)
    counter=f"{until//3600:02d}h {until%3600//60:02d}m"
    status=[pill(stage,"amber" if active else "blue"),html.H3("Response enabled" if state["dr"] else "Response is off"),
        html.P(("Time remaining · " if active else "Next event in · ")+counter,className="event-countdown"),
        html.Div(html.Div(style={"width":f"{max(0,min(100,(seconds-17*3600)/7200*100)):.2f}%"}),className="event-progress")]
    now=[html.Span(f"{seconds//3600:02d}:{seconds%3600//60:02d} · model time",className="eyebrow"),
        html.Div([html.Span("Without response"),html.Strong(f"{result['baseline'].grid_in[i]:.2f} kW")]),
        html.Div([html.Span("Your settings"),html.Strong(f"{result['day'].grid_in[i]:.2f} kW")]),
        html.Small("Schedule-based meter import · animation follows the selected scenario")]
    return status,now


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
               "reference_net_cost_eur", "flex_reward_eur", "grid_carbon_kg_per_kwh", "mode",
               "dr_enabled","dr_lighting_reduction_percent","dr_thermostat_relief_c","dr_shift_cycles","dr_reward_eur_per_kwh"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for i in range(96):
        standing = state["standing"] if i == 0 else 0
        row = [DEMO_DATE.isoformat(), time_label(i), DT, day.load[i], day.pv[i], day.charge[i],
               day.discharge[i], day.soc[i], day.soc[i + 1], day.grid_in[i], day.grid_out[i],
               day.prices[i], state["export_rate"], standing, day.interval_cost[i] + standing,
               day.grid_in[i] * DT * state["carbon"], reference.load[i], reference.grid_in[i], reference.grid_out[i],
               reference.interval_cost[i] + standing, event["reward"] if i == 0 else 0, state["carbon"], "SIMULATED",
               state["dr"],state["dr_dim"],state["dr_relief"],state["dr_shift"],state["dr_reward"]]
        writer.writerow({key: round(float(value), 8) if isinstance(value, (float, np.floating)) else value
                         for key, value in zip(columns, row)})
    return stream.getvalue()


@app.callback(Output("download-data", "data"), Input("export-button", "n_clicks"),
              State("scenario", "data"), prevent_initial_call=True)
def download(n_clicks, raw):
    if not n_clicks:
        raise PreventUpdate
    return dcc.send_string(export_csv(raw), f"smart-simulated-{DEMO_DATE.isoformat()}.csv")


@app.callback(Output("irish-clock","children"),Output("irish-date","children"),Output("analog-clock","src"),
              Input("irish-clock-tick","n_intervals"))
def render_irish_clock(_):
    local=irish_now()
    hands=[]
    for angle,length,width,color in [((local.hour%12+local.minute/60)*30,12,2.5,"#dfead9"),
                                     ((local.minute+local.second/60)*6,17,1.7,"#c4f286"),
                                     (local.second*6,19,.8,"#62d4d6")]:
        theta=math.radians(angle-90)
        hands.append(f'<line x1="25" y1="25" x2="{25+length*math.cos(theta):.2f}" y2="{25+length*math.sin(theta):.2f}" stroke="{color}" stroke-width="{width}" stroke-linecap="round"/>')
    svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"><circle cx="25" cy="25" r="23" fill="#14252b" stroke="#476258"/>'
    svg+=''.join(f'<circle cx="{25+20*math.cos(i*math.pi/6):.2f}" cy="{25+20*math.sin(i*math.pi/6):.2f}" r=".8" fill="#809990"/>' for i in range(12))
    svg+=''.join(hands)+'<circle cx="25" cy="25" r="2" fill="#c4f286"/></svg>'
    return local.strftime("%H:%M:%S")+" "+local.tzname(),local.strftime("%a %d %b · Ireland"),"data:image/svg+xml,"+quote(svg)


@app.callback(Output("live-state","data"),Output("effective-index","data"),
              Input("simulation-tick","n_intervals"),Input("scenario","data"),
              Input("clock-mode","value"),Input("simulation-time","value"),Input("device-overrides","data"),
              State("live-state","data"),State("effective-index","data"))
def advance_simulation(_,raw,mode,manual_slot,overrides,previous,current_index):
    snapshot=step(raw,previous,mode,manual_slot,overrides)
    return snapshot,snapshot["index"] if snapshot["index"]!=current_index else no_update


@app.callback(Output("home-scene","children"),Output("home-scene","triggerRender"),
              Output("home-scene","triggerResetCamera"),
              Output("devices-scene","children"),Output("devices-scene","triggerRender"),
              Output("devices-scene","triggerResetCamera"),
              Output("grid-scene","children"),Output("grid-scene","triggerRender"),
              Output("grid-scene","triggerResetCamera"),Output("scene-memory","data"),
              Input("live-state","data"),Input("home-envelope","value"),Input("devices-envelope","value"),
              Input("grid-envelope","value"),Input("navigation","value"),
              Input("home-zoom","data"),Input("devices-zoom","data"),Input("grid-zoom","data"),
              State("scene-memory","data"),State("scenario","data"),
              running=[(Output("simulation-tick","disabled"), True, False)])
def render_scenes(snapshot,home_mode,device_mode,grid_mode,page,home_zoom,device_zoom,grid_zoom,memory,raw):
    snapshot=snapshot or {}
    memory=dict(memory or {})
    values=[]
    for prefix,mode,visible,zoom_data in [("home",home_mode,page=="overview",home_zoom),
            ("devices",device_mode,page=="devices",device_zoom),("grid",grid_mode,page=="flexibility",grid_zoom)]:
        if not visible:
            values.extend([no_update,no_update,no_update])
            continue
        current=network_snapshot(raw,snapshot) if prefix=="grid" else snapshot
        mode=mode if mode in ("exterior","interior","xray") else "exterior"
        zoom_data=zoom_data or {}
        zoom=max(.55,min(3.5,float(zoom_data.get("factor",1))))
        signature=json.dumps([current.get("lighting_levels",{}),
            {key:float(value)>.001 for key,value in current.get("appliances",{}).items()},
            current.get("sky",{}).get("street_on",False),current.get("dr_active",False),current.get("dr_dim",50),zoom],sort_keys=True)
        # Navigation keeps mounted VTK actors. Resending megabytes of static
        # meshes on every visit can overload a small instance; patch them instead.
        full=memory.get(prefix,{}).get("mode")!=mode
        changed=memory.get(prefix,{}).get("signature")!=signature
        reset=datetime.now(timezone.utc).timestamp() if (ctx.triggered_id==prefix+"-zoom" and zoom_data.get("action")=="reset") or (prefix=="grid" and prefix not in memory) else no_update
        values.extend([scene_children(prefix,mode,current,zoom) if full else scene_patch(prefix,mode,current,changed,zoom),current.get("stamp",0),reset])
        memory[prefix]={"mode":mode,"signature":signature}
    return values+[memory]


def register_viewer_callbacks(prefix):
    @app.callback(Output(prefix+"-scene","cameraPosition"),Output(prefix+"-canvas-wrap","style"),
                  Input(prefix+"-camera","value"),Input(prefix+"-reset-camera","n_clicks"),
                  Input(prefix+"-expand","value"),prevent_initial_call=True)
    def camera(vantage,resets,expand):
        position=CAMERAS.get(vantage,CAMERAS["orbit"])
        position=[value+(resets or 0)*.000001 for value in position]
        return position,{"height":"780px" if "on" in (expand or []) else "530px"}

    @app.callback(Output(prefix+"-zoom","data"),Input(prefix+"-zoom-in","n_clicks"),
                  Input(prefix+"-zoom-out","n_clicks"),Input(prefix+"-reset-camera","n_clicks"),
                  Input(prefix+"-camera","value"),State(prefix+"-zoom","data"),prevent_initial_call=True)
    def zoom_view(zoom_in,zoom_out,resets,vantage,current):
        current=current or {}
        factor=float(current.get("factor",1))
        trigger=ctx.triggered_id
        action="zoom"
        if trigger==prefix+"-zoom-in":
            factor=min(3.5,factor*1.2)
        elif trigger==prefix+"-zoom-out":
            factor=max(.55,factor/1.2)
        else:
            factor,action=1,"reset"
        return {"factor":factor,"action":action,"sequence":int(current.get("sequence",0))+1}

    @app.callback(Output(prefix+"-hover-detail","children"),Input(prefix+"-scene","hoverInfo"),State("live-state","data"))
    def hover(info,snapshot):
        if prefix=="grid":
            return "Blue cable: grid connection · moving particles follow meter flow"
        picked=picked_object(info)
        snapshot=snapshot or {}
        if not picked:
            return "Gold bulbs: lighting · cyan equipment: operating · grey: off / scheduled"
        kind,key=picked
        if kind=="light":
            return f"{ROOMS[key]['name']} · {snapshot.get('lighting_levels',{}).get(key,0):g}% lighting · click to switch On / Off"
        if kind=="device":
            power=snapshot.get("appliances",{}).get(key,0)*1000
            return f"{DEVICES[key]['name']} · {power:.0f} W · click for live On / Off override"
        return ROOMS[key]["name"]


for _prefix in ("home","devices","grid"):
    register_viewer_callbacks(_prefix)


@app.callback(Output("live-metrics","children"),Output("flow-chart","figure"),Output("flow-stats","children"),
    Output("room-detail","children"),Output("live-chart","figure"),Output("live-assets","children"),
    Output("live-session","children"),Output("weather-label","children"),Output("model-time","children"),
    Output("model-mode-label","children"),Output("time-value","children"),
    Output({"type":"live-room","room":ALL},"children"),
    Output({"type":"light-switch-label","room":ALL},"children"),
    Output({"type":"live-device-label","device":ALL},"children"),
    Output("devices-model-time","children"),
    Output({"type":"room-switch","room":ALL},"className"),
    Output({"type":"room-switch","room":ALL},"aria-pressed"),
    Output({"type":"room-tile","room":ALL},"className"),
    Output({"type":"light-detail","room":ALL},"children"),
    Output({"type":"light-meter","room":ALL},"style"),Output("lighting-summary","children"),
    Input("live-state","data"),Input("selected-room","value"),
    State({"type":"live-room","room":ALL},"id"),State({"type":"light-switch-label","room":ALL},"id"),
    State({"type":"live-device-label","device":ALL},"id"))
def render_live(snapshot,room,room_ids,light_ids,device_ids):
    if not snapshot:
        raise PreventUpdate
    room=room if room in ROOMS else "living"
    history=snapshot["history"]
    metrics=[
        metric("Home demand now",f"{snapshot['home']:.3f}","kW","Simulated · refreshes every 2 s","bolt",[r["home"] for r in history]),
        metric("Rooftop solar now",f"{snapshot['pv']:.3f}","kW","13 modules · 5.2 kWp","sun",[r["solar"] for r in history],"cyan"),
        metric("Grid import" if snapshot["import"]>.001 else ("Grid export" if snapshot["export"]>.001 else "Grid balanced"),f"{max(snapshot['import'],snapshot['export']):.3f}","kW",
               "Balanced with home, PV and battery","flex",[r["grid"] for r in history],"blue"),
        metric("Residential battery",f"{snapshot['soc']*10:.1f}","%","10 kWh capacity · 20% reserve","battery",[snapshot["soc"]],"amber")]
    status="Charging" if snapshot["charge"]>.001 else ("Discharging" if snapshot["discharge"]>.001 else "Idle")
    if not snapshot["battery_enabled"]:
        status="Disabled"
    stats=[stat(f"{snapshot['pv']:.2f}","Solar","kW"),stat(f"{snapshot['import']:.2f}","Import","kW"),stat(status,"Battery")]
    detail=[html.Span("SIMULATED INDOOR CONDITIONS",className="eyebrow"),html.H3(ROOMS[room]["name"]),
        html.Div([html.Strong(f"{snapshot['temperatures'][room]:.2f}°"),html.Span("C indoor · RC model")],className="room-power"),
        html.Div([pill(f"{snapshot['room_power'][room]*1000:.0f} W demand","green"),
                  pill(f"{snapshot['lighting_levels'][room]:.0f}% lights","amber")],className="room-pills"),
        html.P(f"Outdoor {snapshot['outdoor']:.1f}°C · thermostat target {snapshot['target']:.1f}°C",className="subtle"),
        html.P("Inside / X-ray exposes the room controls. Select Play day to see thermal changes over an accelerated day.",className="footnote")]
    asset_rows=[
        ("sun","Rooftop PV",f"{snapshot['pv']:.3f} kW", "13 × 400 W modules · front roof"),
        ("car","EV & charger",f"{snapshot['appliances']['ev']:.2f} kW", "Driveway car · charger and cable visible"),
        ("battery","Home battery",f"{snapshot['soc']:.3f} kWh", f"{status} · {max(snapshot['charge'],snapshot['discharge']):.3f} kW"),
        ("climate","Heat pump",f"{snapshot['hvac']:.3f} kW", "Outdoor unit · modelled electrical input")]
    assets=[html.Div([icon(symbol,24),html.Div([html.Strong(label),html.Small(description)]),html.Strong(value)],className="asset-live-row") for symbol,label,value,description in asset_rows]
    session=snapshot["session"]
    session_label=f"This simulation session: {session['energy']:.4f} kWh · variable net cost €{session['cost']:.4f} · {session['carbon']:.4f} kg CO₂e. Standing charge excluded; counters reset when the model time jumps."
    seconds=int(snapshot["seconds"])
    model_time=f"{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}"
    mode_label={"irish":"Europe/Dublin · clock-synchronized simulation","play":"Accelerated model time · ×300","manual":"Fixed time conditions · thermal / battery model evolving"}[snapshot["mode"]]
    rooms=[f"{snapshot['temperatures'][item['room']]:.2f}°C · {snapshot['room_power'][item['room']]*1000:.0f} W" for item in room_ids]
    lights=["ON" if snapshot["lighting_levels"][item["room"]]>0 else "OFF" for item in light_ids]
    devices=[f"{snapshot['appliances'][item['device']]*1000:.0f} W · {snapshot['overrides'][item['device']].upper()}" for item in device_ids]
    classes=["house-switch" if snapshot["lighting_levels"][item["room"]]>0 else "house-switch off" for item in light_ids]
    pressed=["true" if snapshot["lighting_levels"][item["room"]]>0 else "false" for item in light_ids]
    tiles=["room-control-row light-tile "+("is-on" if snapshot["lighting_levels"][item["room"]]>0 else "is-off") for item in light_ids]
    details=[f"{snapshot['lighting_levels'][item['room']]:g}% brightness · {snapshot['lights'][item['room']]*1000:.1f} W lighting" for item in light_ids]
    meters=[{"width":f"{snapshot['lighting_levels'][item['room']]:g}%"} for item in light_ids]
    summary=[html.Strong(f"{sum(value>0 for value in snapshot['lighting_levels'].values())} / 6 rooms lit"),
             html.Span(f"{sum(snapshot['lights'].values())*1000:.1f} W total lighting")]
    return (metrics,charts.live_flow(snapshot),stats,detail,charts.live_profile(snapshot),assets,session_label,
        f"{snapshot['outdoor']:.1f}°C",model_time,mode_label,model_time[:5],rooms,lights,devices,
        model_time+" · "+mode_label,classes,pressed,tiles,details,meters,summary)


@app.callback(Output("clock-mode","value"),Output("simulation-time","value"),
    Input("devices-play","n_clicks"),Input("devices-irish","n_clicks"),
    Input("devices-day","n_clicks"),Input("devices-night","n_clicks"),
    Input("dr-preview","n_clicks"),Input("dr-irish","n_clicks"),prevent_initial_call=True)
def set_devices_clock(*clicks):
    trigger=ctx.triggered_id
    if trigger=="devices-play":
        return "play",no_update
    slots={"devices-day":52,"devices-night":84,"dr-preview":72}
    if trigger in slots:
        return "manual",slots[trigger]
    return "irish",no_update


def register_sky_callback(prefix):
    @app.callback(Output(prefix+"-scene","background"),Output(prefix+"-sky-dressing","className"),
        Output(prefix+"-sky-orb","className"),Output(prefix+"-sky-orb","style"),
        Output(prefix+"-sky-label","children"),Output(prefix+"-sky-status","children"),Input("live-state","data"))
    def draw_sky(snapshot):
        if not snapshot or "sky" not in snapshot:
            raise PreventUpdate
        sky=snapshot["sky"]
        caption=[html.Strong("Daylight" if sky["daylight"] else "After sunset"),
            html.Span(sky["local_time"]+" · Dublin model time")]
        status=[html.Span(f"Sunrise {sky['sunrise']} · Sunset {sky['sunset']} · {sky['date']}"),
            html.Strong("Street lights ON · automatic" if sky["street_on"] else "Street lights OFF · daylight"),
            html.Small("Public street lighting is outside the home's energy meter. Moon is a night symbol.")]
        return (sky["background"],"sky-dressing "+sky["phase"],"sky-orb "+sky["orb"],
            {"left":f"{sky['orb_left']:.2f}%"},caption,status)


for _sky_prefix in ("home","devices","grid"):
    register_sky_callback(_sky_prefix)


from security import install as install_security
install_security(app)


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8050")), debug=False)

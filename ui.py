"""Dash components, including vector icons authored in Python."""
from urllib.parse import quote
from dash import dcc, html
import numpy as np
from energy import DEFAULT, DEVICES, ROOMS

PATHS = {
    "bolt": "M13 2 4 14h7l-1 8 10-12h-7l0-8Z",
    "home": "m3 10 9-7 9 7v10h-6v-7H9v7H3Z",
    "grid": "M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z",
    "devices": "M3 4h12v13H3ZM7 21h4M18 8h4v13h-4Z",
    "climate": "M9 14V5a3 3 0 0 1 6 0v9a5 5 0 1 1-6 0ZM12 8v10",
    "chart": "M3 3v18h18M7 15l4-5 4 3 6-8",
    "flex": "m3 8 4-4 4 4M7 4v13M21 16l-4 4-4-4M17 20V7",
    "settings": "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2",
    "sun": "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10ZM12 1v3M12 20v3M1 12h3M20 12h3M4 4l2 2M18 18l2 2M4 20l2-2M18 6l2-2",
    "leaf": "M20 3C7 1 1 10 6 17c7 7 16-2 14-14ZM5 21 16 9M9 15H5M13 11V7",
    "wallet": "M3 5h16v15H3ZM3 5V3h14v2M15 10h6v6h-6ZM18 13h.01",
    "battery": "M2 6h18v12H2ZM22 10v4M6 10v4M10 10v4M14 10v4",
    "bulb": "M8 16c0-3-3-3-3-7a7 7 0 0 1 14 0c0 4-3 4-3 7ZM9 20h6M10 23h4",
    "washer": "M3 3h18v18H3ZM3 7h18M6 5h.01M10 5h.01M12 10a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z",
    "appliance": "M4 3h16v18H4ZM4 8h16M8 5h.01M12 5h.01M8 12h8v6H8Z",
    "water": "M12 2C10 6 5 11 5 15a7 7 0 0 0 14 0c0-4-5-9-7-13ZM9 15c0 2 1 3 3 3",
    "car": "m5 5-2 7v7h3v-3h12v3h3v-7l-2-7ZM3 12h18M7 14h.01M17 14h.01M5 5h14",
    "monitor": "M2 3h20v14H2ZM8 21h8M12 17v4",
    "arrow": "M5 12h14m-5-5 5 5-5 5",
    "download": "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
    "info": "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20ZM12 11v6M12 7h.01",
    "check": "m5 12 4 4L19 6",
    "moon": "M20 15A9 9 0 0 1 9 4a9 9 0 1 0 11 11Z",
    "cloud": "M5 18a5 5 0 0 1-1-10 7 7 0 0 1 13-2 6 6 0 1 1 1 12ZM8 21h8",
}


def icon(name, size=19, color="currentColor", className=""):
    # SVG is presentation only; application behavior is exclusively Python callbacks.
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color if color != "currentColor" else "#b5c4c8"}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="{PATHS.get(name, PATHS["bolt"])}"/></svg>'
    return html.Img(src="data:image/svg+xml," + quote(svg), alt="", width=size, height=size, className="icon " + className)


def graph(graph_id, height=280):
    return dcc.Graph(id=graph_id, config={"displayModeBar": False, "displaylogo": False, "scrollZoom": False},
                     responsive=True, style={"height": f"{height}px"}, className="chart")


def heading(title, subtitle=None, aside=None):
    return html.Div([html.Div([html.H3(title), html.P(subtitle, className="subtle") if subtitle else None]), aside], className="card-heading")


def card(children, className="", **kwargs):
    return html.Section(children, className="card " + className, **kwargs)


def pill(text, kind=""):
    return html.Span(text, className="pill " + kind)


def switch(component_id, label, on=True, className=""):
    return dcc.Checklist(id=component_id, options=[{"label": label, "value": "on"}],
                         value=["on"] if on else [], className="switch " + className,
                         inputClassName="switch-input", labelClassName="switch-label")


def sparkline(values, color="#c4f286"):
    values = np.asarray(values, dtype=float)
    if len(values) > 32:
        values = values[::3]
    low, high = values.min(), values.max()
    scale = high - low if high > low else 1
    points = " ".join(f"{i * 120 / max(len(values)-1, 1):.1f},{29 - (v-low)/scale*24:.1f}" for i, v in enumerate(values))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 122 34"><polyline fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" points="{points}"/></svg>'
    return html.Img(src="data:image/svg+xml," + quote(svg), alt="Trend for simulated day", className="sparkline")


def metric(label, value, unit, note, symbol, values, tone="green"):
    return card([
        html.Div([html.Span(label), html.Span(icon(symbol, 17), className="metric-icon " + tone)], className="metric-top"),
        html.Div([html.Strong(value), html.Span(unit, className="metric-unit")], className="metric-value"),
        html.Div([html.Span(note, className="metric-note"), sparkline(values, {"green": "#c4f286", "cyan": "#62d4d6", "amber": "#edbd81", "blue": "#83a9f5"}[tone])], className="metric-bottom")
    ], "metric")


def sidebar():
    labels = [("overview", "grid", "Overview"), ("devices", "devices", "Devices & lighting"),
              ("climate", "climate", "Heating & cooling"), ("analytics", "chart", "Energy analytics"),
              ("flexibility", "flex", "Demand response"), ("settings", "settings", "System & assumptions")]
    return html.Aside([
        html.Div([html.Span(icon("bolt", 27, "#101a13"), className="brand-mark"),
                  html.Div([html.Strong("verdant"), html.Span("HOME ENERGY")])], className="brand"),
        html.Div([html.Span("MY WORKSPACE", className="eyebrow"),
                  html.Div([icon("home", 18), html.Div([html.Strong("The Green House"), html.Span("Dublin · demo residence")]), html.Span("⌄")], className="home-selector")], className="workspace-select"),
        html.P("MANAGE YOUR HOME", className="nav-caption"),
        dcc.RadioItems(id="navigation", value="overview", options=[
            {"value": key, "label": html.Span([icon(symbol, 18), html.Span(label)], className="nav-label")}
            for key, symbol, label in labels], className="navigation", inputClassName="nav-input"),
        html.Div([
            html.Div([icon("leaf", 24, "#c4f286"), html.Span("Small changes.\nLasting impact.")], className="sidebar-message"),
            html.P("Explore what a more efficient home could look like.", className="subtle"),
            pill("ENERGY IN BALANCE", "muted")
        ], className="sidebar-bottom"),
        html.Div([html.Span("VE", className="avatar"), html.Div([html.Strong("Examiner workspace"), html.Small("Interactive demonstration")])], className="profile")
    ], className="sidebar")


def overview():
    return html.Div([
        html.Div([html.Div([html.Div([html.Span("YOUR HOME, IN BALANCE", className="eyebrow"), pill("SIMULATED", "demo")], className="intro-eyebrow"),
                  html.H1(["A smarter home. ", html.Span("A lighter footprint.")]),
                  html.P("See where your energy goes. Take control of what comes next.", className="intro-subtitle")]),
                  html.Div([icon("cloud", 28, "#cbdad5"), html.Div([html.Strong(id="weather-label"), html.Span("Outdoor · simulated autumn day")])], className="weather")], className="intro"),
        html.Div(id="overview-metrics", className="metrics-grid"),
        html.Div([
            card([
                heading("Your home, connected", "A room-by-room view of your energy", pill("6 ROOMS · 128 m²", "muted")),
                html.Div([dcc.RadioItems(id="house-layer", options=[{"label": "Rooms", "value": "rooms"}, {"label": "Energy", "value": "power"}, {"label": "Lighting", "value": "lights"}], value="rooms", className="segments compact"),
                          html.Span([html.Span(className="status-dot"), "Interactive 3D twin"], className="subtle")], className="house-toolbar"),
                dcc.Graph(id="house-view", config={"displayModeBar": False, "displaylogo": False, "scrollZoom": True}, responsive=True, style={"height": "445px"}),
                html.Div([html.Span("↔  Drag to orbit · scroll to zoom · click a room"),
                    dcc.Dropdown(id="selected-room", options=[{"label": r["name"], "value": key} for key, r in ROOMS.items()], value="living", clearable=False, searchable=False, className="room-dropdown")], className="house-caption")
            ], "house-card"),
            html.Div([
                card([heading("Energy flow", "At the selected simulation time", pill("kW", "muted")),
                    graph("flow-chart", 205), html.Div(id="flow-stats", className="flow-stats")], "flow-card"),
                card([html.Div(id="room-detail")], "room-card"),
            ], className="house-side")
        ], className="house-grid"),
        card([html.Div([html.Div([icon("sun", 19, "#c4f286"), html.Strong("Explore your day"), html.Span("15-minute intervals · controls replay the whole day", className="subtle")], className="inline"),
                            html.Strong(id="time-value", className="time-value")], className="timeline-top"),
              dcc.Slider(id="simulation-time", min=0, max=95, step=1, value=57,
                  marks={0: "00:00", 24: "06:00", 48: "12:00", 72: "18:00", 95: "23:45"},
                  tooltip={"always_visible": False}),
        ], "timeline-card"),
        html.Div([
            card([heading("Energy throughout the day", "Full-day scenario · power in kW"), graph("daily-chart", 268)], "profile-card"),
            card([heading("Electricity tariff", "Illustrative rates · editable in System"),
                  html.Div(id="price-current", className="price-current"), graph("price-chart", 165),
                  html.Div([pill("00–07  OFF-PEAK", "blue"), pill("17–19  PEAK", "amber")], className="tariff-labels")])
        ], className="two-col wide-left"),
        html.Div(id="recommendations", className="recommendations")
    ], id="page-overview", className="page")


def devices():
    device_cards = []
    for key, item in DEVICES.items():
        device_cards.append(card([
            html.Div([html.Span(icon(item["icon"], 24, "#b9d2c3"), className="device-icon"),
                      pill("FLEXIBLE" if item["flex"] else "FIXED WINDOW", "green" if item["flex"] else "muted")], className="device-top"),
            html.H3(item["name"]), html.P(ROOMS[item["room"]]["name"], className="subtle"),
            html.P(item["description"], className="device-spec"),
            html.Div(id={"type": "device-status", "device": key}, className="device-status"),
            switch({"type": "device-toggle", "device": key}, "Enable daily schedule", DEFAULT["devices"][key]),
        ], "device-card"))
    light_cards = []
    for room, info in ROOMS.items():
        light_cards.append(card([
            html.Div([icon("bulb", 22, "#edbd81"), html.H3(info["name"]),
                      html.Strong(id={"type": "brightness-label", "room": room})], className="light-title"),
            dcc.Slider(id={"type": "brightness", "room": room}, min=0, max=100, step=5, value=65,
                       marks={0: "Off", 50: "50%", 100: "100%"}),
            html.P(f"{info['lights_w']} W at full brightness · daylight dimming enabled", className="subtle")
        ], "light-card"))
    return html.Div([
        html.Div([html.Div([html.H1("Every device. One place."), html.P("Change a daily schedule or dim a room and see the energy model respond.", className="intro-subtitle")]),
                  pill("SIMULATED CONTROLS", "demo")], className="page-intro"),
        html.Div(device_cards, className="three-col"),
        html.Div([html.Div([html.H2("Lighting, room by room"), html.P("Brightness is a scenario setting; daylight uses 30% of the selected power from 08:00 to 17:00.", className="subtle")]),
            html.Div([html.Label("QUICK SCENE", className="eyebrow"), dcc.Dropdown(id="scene", options=["Home", "Eco", "Away"], value="Home", clearable=False, searchable=False, className="scene-dropdown")], className="scene-control")], className="section-title"),
        html.Div(light_cards, className="three-col"),
        card([heading("Your appliance schedule", "Enabled devices only · one full cycle per day"),
            switch("optimizer-toggle", "Schedule flexible loads at the cheapest tariff", False),
            graph("schedule-chart", 285), html.P("Tariff-only scheduling searches every contiguous cycle in the day. It assumes devices can run unattended at any time and does not guarantee the lowest whole-home bill.", className="footnote")]),
        html.Div([icon("info", 17), html.Span("The fridge, router and standby load remain enabled: 110 W combined. Device toggles enable a daily operating window; they do not command real appliances.")], className="notice")
    ], id="page-devices", className="page hidden")


def climate_page():
    return html.Div([
        html.Div([html.Div([html.H1("Comfort, with a conscience."), html.P("Explore the energy trade-off of your thermostat and operating mode.", className="intro-subtitle")]), pill("HEAT PUMP MODEL", "muted")], className="page-intro"),
        html.Div([
            card([heading("Whole-home thermostat", "Target temperature · simulated control"),
                html.Div([html.Div("TARGET", className="eyebrow"), html.Div(id="thermostat-value", className="thermostat-value"), html.P("°C setpoint", className="subtle")], className="thermostat-dial"),
                dcc.Slider(id="thermostat", min=16, max=26, step=.5, value=21,
                    marks={16: "16°", 18: "18°", 20: "20°", 22: "22°", 24: "24°", 26: "26°"}),
                dcc.RadioItems(id="hvac-mode", options=[{"label": "Heating", "value": "heat"}, {"label": "Cooling", "value": "cool"}, {"label": "Off", "value": "off"}], value="heat", className="segments"),
                html.P("The model estimates electricity needed to maintain a target. It does not predict measured indoor temperatures.", className="footnote")], "thermostat-card"),
            card([heading("Climate profile", "Synthetic outdoor temperature and thermostat target"), graph("climate-chart", 280), html.Div(id="climate-summary", className="stat-strip")])
        ], className="two-col narrow-left"),
        html.Div([
            card([heading("Heating & cooling demand", "Electrical input · heat-pump model"), graph("climate-load", 260)]),
            card([heading("How the estimate works", "Transparent assumptions"),
                html.Div([html.Strong("0.18"), html.Span("kW/°C · whole-home heat-loss coefficient")], className="assumption-row"),
                html.Div([html.Strong("3.5 / 3.2"), html.Span("Heating COP / cooling COP · constant")], className="assumption-row"),
                html.Div([html.Strong("1°C"), html.Span("Target relief during an opted-in flex event")], className="assumption-row"),
                html.P("A quasi-steady balance includes outdoor temperature and simple passive gains. Thermal storage, humidity, room sensors, weather forecasts and equipment cycling are outside this demonstration.", className="footnote")])
        ], className="two-col")
    ], id="page-climate", className="page hidden")


def analytics():
    return html.Div([
        html.Div([html.Div([html.H1("Make every kilowatt count."), html.P("Compare your settings with a declared reference, using the same synthetic weather and tariff.", className="intro-subtitle")]),
                  dcc.RadioItems(id="analytics-range", options=[{"label": "7 days", "value": 7}, {"label": "30 days", "value": 30}], value=7, className="segments")], className="page-intro"),
        html.Div(id="analytics-metrics", className="metrics-grid"),
        html.Div([
            card([heading("Electricity cost", "Net import cost after export credit · includes daily standing charge · excludes flex rewards"), graph("cost-comparison", 280)]),
            card([heading("Where your energy goes", "Full-day end-use demand · current scenario"), graph("breakdown-chart", 250)])
        ], className="two-col wide-left"),
        html.Div([
            card([heading("Energy demand", "End-use consumption · solar generation does not reduce demand"), graph("load-comparison", 280)]),
            card([heading("Operational carbon", "Grid imports × assumed emission factor · no export offsets"), graph("carbon-comparison", 280)])
        ], className="two-col"),
        card([heading("Scenario ledger", "Synthetic replay of current controls · not recorded historical performance"), html.Div(id="scenario-ledger", className="table-wrap")]),
        html.Div([icon("info", 18), html.Span("Reference: 22°C heating, 80% lighting, default appliance schedules, your selected solar availability, and battery disabled. Initial battery energy is disclosed in System. Negative savings mean the scenario performs worse.")], className="notice")
    ], id="page-analytics", className="page hidden")


def flexibility():
    return html.Div([
        html.Div([html.Div([html.H1("A flexible home. A stronger grid."), html.P("Test a demand-response event and see what changes during the evening peak.", className="intro-subtitle")]), pill("PROGRAM SIMULATOR", "demo")], className="page-intro"),
        card([
            html.Div([html.Div([pill("ILLUSTRATIVE EVENT", "green"), html.H2("Give the grid a little breathing room."),
                html.P("17:00–19:00 · 2-hour peak reduction window", className="intro-subtitle"),
                html.Div([html.Span("€0.35"), html.Small("per kWh of modelled import reduction")], className="reward-rate")]),
                html.Div([icon("flex", 62, "#c4f286"), switch("dr-toggle", "Participate in this simulation", False)], className="event-action")], className="event-banner"),
            html.P("Opting in reschedules flexible cycles outside the event, halves lighting power during the event, and relaxes the thermostat by 1°C. No enrollment or payment takes place.", className="footnote")
        ], "event-card"),
        html.Div(id="dr-metrics", className="three-col"),
        html.Div([
            card([heading("Peak-window comparison", "Matched counterfactual: same settings and battery, with demand response disabled"), graph("dr-chart", 295)]),
            card([heading("Your flexibility plan", "Changes applied only when participation is enabled"),
                html.Div([icon("appliance", 23), html.Div([html.Strong("Move flexible cycles"), html.P("Washer, dishwasher, hot water and EV charging avoid 17:00–19:00.")])], className="plan-row"),
                html.Div([icon("bulb", 23), html.Div([html.Strong("Dim the lights"), html.P("50% less lighting power within the event window.")])], className="plan-row"),
                html.Div([icon("climate", 23), html.Div([html.Strong("Ease the thermostat"), html.P("Heating target −1°C; cooling target +1°C during the event.")])], className="plan-row"),
                html.P("Reward = max(0, matched import reduction in kWh) × €0.35. This simplified model is not a supplier's settlement or eligibility calculation.", className="footnote")])
        ], className="two-col wide-left")
    ], id="page-flexibility", className="page hidden")


def settings():
    fields = [("offpeak", "Off-peak import", "€/kWh · 00:00–07:00", .16, 2),
              ("day", "Day import", "€/kWh · remaining hours", .28, 2),
              ("peak", "Peak import", "€/kWh · 17:00–19:00", .42, 2),
              ("export_rate", "Export credit", "€/kWh exported", .12, 1),
              ("standing", "Standing charge", "€/day · added once per model day", .65, 5),
              ("carbon", "Grid emission factor", "kg CO₂e/kWh imported", .23, 1)]
    return html.Div([
        html.Div([html.Div([html.H1("A model you can inspect."), html.P("Every tariff, assumption and boundary is visible. Nothing here is a live supplier feed.", className="intro-subtitle")]), pill("DEMONSTRATION MODE", "demo")], className="page-intro"),
        html.Div([
            card([heading("Tariff & carbon assumptions", "EUR · illustrative time-of-use rates; not a supplier quote"),
                html.Div([html.Div([html.Label(label, htmlFor="setting-" + key), html.Small(note),
                    dcc.Input(id="setting-" + key, type="number", value=val, min=0, max=maximum,
                              step=.01, debounce=True, className="number-input")], className="setting-field")
                    for key, label, note, val, maximum in fields], className="settings-fields"),
                html.P("These are editable teaching assumptions, not verified Irish market prices, grid intensity or bill estimates. Blank/invalid values fall back to defaults; values are bounded server-side.", className="footnote")]),
            card([heading("Home energy assets", "Self-consumption dispatch · no grid charging"),
                html.Div([html.Div([icon("sun", 25), html.Div([html.Strong("Rooftop solar"), html.P("5.2 kWp · synthetic autumn generation")])]), switch("solar-toggle", "Enable solar array", True)], className="asset-setting"),
                html.Div([html.Div([icon("battery", 25), html.Div([html.Strong("Home battery"), html.P("10 kWh · 2.5 kW charge / discharge")])]), switch("battery-toggle", "Enable battery dispatch", True)], className="asset-setting"),
                html.Div([html.Strong("90%"), html.Span("Round-trip efficiency · symmetric conversion losses")], className="assumption-row"),
                html.Div([html.Strong("20%"), html.Span("Minimum state of charge · 2 kWh reserve")], className="assumption-row"),
                html.Div([html.Strong("50%"), html.Span("Initial state of charge · reset at each model day")], className="assumption-row")])
        ], className="two-col"),
        card([heading("What the results mean", "Methodology for assessment"),
            html.Div([
                html.Div([html.H3("Energy & cost"), html.P("Each interval is 15 minutes: energy (kWh) = power (kW) × 0.25 h. Daily cost = import energy × import tariff − export energy × export credit + standing charge. Flex rewards are shown separately and included only in the explicitly labelled savings metric.")]),
                html.Div([html.H3("Carbon & savings"), html.P("Operational emissions = imported electricity × the assumed constant grid factor. Avoided emissions and savings are the declared reference minus your scenario. Battery manufacture, PV lifecycle emissions, fuel use and export carbon offsets are excluded.")]),
                html.Div([html.H3("Battery boundary"), html.P("Battery dispatch uses solar surplus first and discharges into demand above its reserve. Every model day starts with 5 kWh already stored, with no acquisition cost or emissions assigned. Daily comparisons are therefore illustrative and may benefit from a net drawdown. End-of-day charge is shown; multi-day charts replay independent days rather than carrying battery state forward.")]),
                html.Div([html.H3("Demonstration scope"), html.P("The house is an illustrative 3D model, not a surveyed digital twin. Room power allocates HVAC and always-on load by floor area. Controls are isolated in each browser session and replay a full scenario day; they are not time-stamped commands or measured history. No real devices, provider APIs or AI service are connected.")])
            ], className="methodology-grid")]),
        card([heading("Examiner walkthrough", "A five-minute demonstration"), html.Ol([
            html.Li("Explore the 3D house, choose a room and move the simulation-time slider."),
            html.Li("Open Devices & lighting. Try the Eco scene, then enable cheapest-tariff scheduling."),
            html.Li("Change the heat-pump target in Heating & cooling and inspect demand."),
            html.Li("Participate in the Demand response simulation and compare the peak window."),
            html.Li("Inspect Energy analytics, then export the quarter-hour CSV to verify the calculations.")
        ], className="walkthrough")])
    ], id="page-settings", className="page hidden")


def layout(today):
    return html.Div([
        dcc.Store(id="scenario", data=DEFAULT, storage_type="memory"),
        dcc.Download(id="download-data"), sidebar(),
        html.Main([
            html.Header([
                html.Div([html.Span("Workspace", className="subtle"), html.Span("/", className="breadcrumb-divider"), html.Strong("Overview", id="page-title")], className="breadcrumb"),
                html.Div([html.Span([html.Span(className="status-dot"), "SIMULATION"], className="header-status"),
                          html.Span(today.strftime("%a, %d %b %Y"), className="header-date"),
                          html.Button([icon("download", 15), "Export CSV"], id="export-button", className="button secondary")], className="header-actions")
            ], className="topbar"),
            html.Div([overview(), devices(), climate_page(), analytics(), flexibility(), settings()], className="page-content"),
            html.Footer([html.Span([html.Strong("verdant"), " · Home Energy Management"]), html.Span("Scenario mode · Synthetic data only")], className="footer")
        ], className="main-content")
    ], className="app-shell")

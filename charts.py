"""Python/Plotly chart builders shared by the dashboard views."""
import numpy as np
import plotly.graph_objects as go
from energy import HOURS, DT, DEVICES, time_label

GREEN = "#c4f286"
CYAN = "#62d4d6"
BLUE = "#83a9f5"
MUTED = "#85959e"
GRID = "#26343b"


def style(fig, height=285):
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Segoe UI, sans-serif", color=MUTED, size=11),
        margin=dict(l=12, r=12, t=20, b=20), height=height,
        legend=dict(orientation="h", y=1.16, x=0, font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified", hoverlabel=dict(bgcolor="#20313a", font_size=12),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False))
    return fig


def day_axis(fig, title=None):
    fig.update_xaxes(tickvals=[0, 4, 8, 12, 16, 20, 24],
                     ticktext=["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "24:00"],
                     range=[0, 24])
    if title:
        fig.update_yaxes(title_text=title, title_font_size=10)
    return fig


def profile(day, index):
    fig = go.Figure()
    for name, values, color, fill in [
        ("Home demand", day.load, GREEN, "tozeroy"),
        ("Solar generation", day.pv, CYAN, None),
        ("Grid import", day.grid_in, BLUE, None),
    ]:
        fig.add_trace(go.Scatter(x=HOURS.tolist(), y=values.tolist(), name=name, mode="lines",
            line=dict(color=color, width=2.2, shape="spline"), fill=fill,
            fillcolor="rgba(196,242,134,.08)", hovertemplate="%{y:.2f} kW"))
    fig.add_vrect(x0=17, x1=19, fillcolor="#f3b772", opacity=.06, line_width=0)
    fig.add_vline(x=index * DT, line_color="#667c82", line_dash="dot", line_width=1)
    return day_axis(style(fig, 268), "Power · kW")


def price(day, index, tall=False):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=HOURS.tolist(), y=(day.prices * 100).tolist(),
        line=dict(color="#edbd81", width=2.3, shape="hv"), fill="tozeroy",
        fillcolor="rgba(237,189,129,.07)", hovertemplate="%{y:.1f} c/kWh", name="Import tariff"))
    fig.add_trace(go.Scatter(x=[index * DT], y=[day.prices[index] * 100], mode="markers",
        marker=dict(size=8, color="#edbd81"), showlegend=False, hoverinfo="skip"))
    return day_axis(style(fig, 290 if tall else 165), "c/kWh" if tall else None)


def flow(day, index):
    solar_direct = min(day.pv[index], day.load[index])
    values = [solar_direct, day.charge[index], day.grid_out[index],
              day.discharge[index], day.grid_in[index]]
    fig = go.Figure(go.Sankey(arrangement="fixed",
        node=dict(label=["Solar", "Battery", "Grid", "Home", "Export"],
            x=[.01, .48, .01, .99, .99], y=[.05, .68, .95, .12, .95],
            color=[CYAN, GREEN, BLUE, "#bedb9b", "#657d92"], pad=17, thickness=10,
            line=dict(width=0)),
        link=dict(source=[0, 0, 0, 1, 2], target=[3, 1, 4, 3, 3],
            value=[float(v) for v in values],
            color=["rgba(98,212,214,.24)", "rgba(98,212,214,.18)", "rgba(98,212,214,.15)",
                   "rgba(196,242,134,.28)", "rgba(131,169,245,.24)"],
            hovertemplate="%{value:.2f} kW<extra></extra>"), valueformat=".2f", valuesuffix=" kW"))
    style(fig, 205)
    fig.update_layout(margin=dict(l=15, r=35, t=18, b=18), font_size=11)
    return fig


def breakdown(day):
    labels = list(day.loads)
    values = [float(v.sum() * DT) for v in day.loads.values()]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=.74, sort=False,
        marker=dict(colors=[GREEN, "#edbd81", CYAN, BLUE], line=dict(color="#142028", width=3)),
        textinfo="none", hovertemplate="%{label}<br>%{value:.2f} kWh · %{percent}<extra></extra>"))
    style(fig, 250)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=-.08, x=.05, font_size=10),
        annotations=[dict(text=f"<b>{day.totals['load']:.1f}</b><br>kWh / day", x=.5, y=.5,
                         showarrow=False, font=dict(size=20, color="#eaf1e8"))],
        margin=dict(l=10, r=10, t=0, b=25))
    return fig


def climate(day, index):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=HOURS.tolist(), y=day.outdoor.tolist(), name="Outdoor assumption",
        line=dict(color=CYAN, width=2), hovertemplate="%{y:.1f} °C"))
    if day.state["hvac"] != "off":
        target = np.full(96, day.state["temperature"])
        if day.state["dr"]:
            target[68:76] += -1 if day.state["hvac"] == "heat" else 1
        fig.add_trace(go.Scatter(x=HOURS.tolist(), y=target.tolist(), name="Thermostat target",
            line=dict(color=GREEN, width=2, dash="dot"), hovertemplate="%{y:.1f} °C"))
    fig.add_vline(x=index * DT, line_dash="dot", line_color="#61747b")
    return day_axis(style(fig, 280), "Temperature · °C")


def climate_load(day):
    fig = go.Figure(go.Scatter(x=HOURS.tolist(), y=day.loads["Heating & cooling"].tolist(),
        line=dict(color="#edbd81", width=2), fill="tozeroy", fillcolor="rgba(237,189,129,.1)",
        name="HVAC demand", hovertemplate="%{y:.2f} kW"))
    return day_axis(style(fig, 260), "Electrical power · kW")


def demand_response(day, event):
    fig = go.Figure()
    for name, values, color, dash in [("Without event", event["counterfactual"].grid_in, MUTED, "dot"),
                                       ("Your scenario", day.grid_in, GREEN, "solid")]:
        fig.add_trace(go.Scatter(x=HOURS.tolist(), y=values.tolist(), name=name,
            line=dict(color=color, width=2, dash=dash), hovertemplate="%{y:.2f} kW"))
    fig.add_vrect(x0=17, x1=19, fillcolor=GREEN, opacity=.09, line_width=0,
                  annotation_text="Flex event", annotation_font_color=GREEN)
    day_axis(style(fig, 295), "Grid import · kW")
    fig.update_xaxes(range=[15, 21], tickvals=[15, 16, 17, 18, 19, 20, 21],
                     ticktext=[f"{h}:00" for h in range(15, 22)])
    return fig


def comparison(rows, kind="cost"):
    fig = go.Figure()
    label, refkey, unit = {"cost": ("cost", "reference_cost", "€"),
                          "load": ("load", "reference_load", "kWh"),
                          "carbon": ("carbon", "reference_carbon", "kg CO₂e")}[kind]
    for name, key, color in [("Reference", refkey, "#40545f"), ("Your scenario", label, GREEN)]:
        fig.add_trace(go.Bar(x=[r["date"] for r in rows], y=[r[key] for r in rows],
            name=name, marker_color=color, hovertemplate=f"%{{y:.2f}} {unit}"))
    style(fig, 280)
    fig.update_layout(barmode="group", bargap=.3)
    fig.update_yaxes(title_text=unit, title_font_size=10)
    return fig


def schedule(day):
    fig = go.Figure()
    for key, device in DEVICES.items():
        item = day.schedules[key]
        if not day.state["devices"][key]:
            continue
        fig.add_trace(go.Bar(y=[device["name"]], x=[(item["end"] - item["start"]) * DT],
            base=[item["start"] * DT], orientation="h", marker_color=GREEN if device["flex"] else CYAN,
            name=device["name"], hovertemplate=f"{time_label(item['start'])}–{time_label(item['end'])}<br>{item['energy']:.2f} kWh<extra></extra>",
            showlegend=False))
    style(fig, 285)
    day_axis(fig)
    fig.update_layout(margin=dict(l=10, r=10, t=12, b=20), barmode="overlay")
    fig.update_xaxes(showgrid=True, gridcolor=GRID)
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def live_profile(snapshot):
    history = snapshot.get("history", [])
    fig = go.Figure()
    for key, label, color in [("home","Home demand",GREEN),("solar","Solar",CYAN),("grid","Grid import",BLUE)]:
        fig.add_trace(go.Scatter(x=list(range(len(history))), y=[r[key] for r in history],
            mode="lines",name=label,line=dict(color=color,width=2.1),
            customdata=[r["time"] for r in history], hovertemplate="%{customdata}<br>%{y:.3f} kW<extra></extra>"))
    style(fig,245)
    step=max(1,len(history)//5)
    ticks=list(range(0,len(history),step))
    fig.update_layout(uirevision="live-energy",margin=dict(l=12,r=12,t=35,b=25),
        xaxis=dict(tickvals=ticks,ticktext=[history[i]["time"] for i in ticks],showgrid=False),
        yaxis=dict(title="kW",gridcolor=GRID,rangemode="tozero"))
    return fig


def live_flow(snapshot):
    from types import SimpleNamespace
    return flow(SimpleNamespace(pv=[snapshot.get("pv",0)],load=[snapshot.get("home",0)],
        charge=[snapshot.get("charge",0)],discharge=[snapshot.get("discharge",0)],
        grid_in=[snapshot.get("import",0)],grid_out=[snapshot.get("export",0)]),0)

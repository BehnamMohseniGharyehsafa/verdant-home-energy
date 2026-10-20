"""A furnished, explorable cutaway home, constructed entirely with Plotly in Python."""
import math
import numpy as np
import plotly.graph_objects as go
from energy import ROOMS, room_power

FLOORS = {
    "living": (0, 0, 7, 4.2), "kitchen": (7, 0, 12, 4.2),
    "bedroom": (0, 4.2, 4.5, 9), "bathroom": (4.5, 4.2, 7, 9),
    "office": (7, 4.2, 12, 9), "garage": (12, 4, 16, 9),
}


def box(fig, x, y, z, width, depth, height, color, room=None, opacity=1, name=""):
    vertices = [(x, y, z), (x + width, y, z), (x + width, y + depth, z), (x, y + depth, z),
                (x, y, z + height), (x + width, y, z + height),
                (x + width, y + depth, z + height), (x, y + depth, z + height)]
    a, b, c = zip(*[(0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                  (0, 4, 5), (0, 5, 1), (1, 5, 6), (1, 6, 2),
                  (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0)])
    vx, vy, vz = zip(*vertices)
    fig.add_trace(go.Mesh3d(x=vx, y=vy, z=vz, i=a, j=b, k=c, color=color,
        opacity=opacity, flatshading=True, lighting=dict(ambient=0.65, diffuse=0.85,
        specular=0.18, roughness=0.85), lightposition=dict(x=0, y=-20, z=40),
        customdata=[room] * 8,
        hovertemplate=(f"{name}<extra></extra>" if name else "<extra></extra>"),
        showlegend=False))


def house_figure(day, index=57, selected="living", layer="rooms"):
    fig = go.Figure()
    box(fig, -1.0, -1.0, -0.4, 18, 11, 0.22, "#263a35")
    box(fig, -0.2, -0.2, -0.2, 12.4, 9.4, 0.2, "#c0b8a5")
    colors = {"living": "#b3c4ac", "kitchen": "#c4c7b7", "bedroom": "#b8c4ce",
              "bathroom": "#92b4b7", "office": "#c6baa2", "garage": "#959e9a"}
    for room, (x1, y1, x2, y2) in FLOORS.items():
        power = room_power(day, room, index)
        color = colors[room]
        if layer == "power":
            amount = min(power / 1.5, 1)
            color = f"rgb({int(112 + 110 * amount)},{int(190 - 65 * amount)},{int(173 - 80 * amount)})"
        elif layer == "lights":
            level = day.state["lights"][room] / 100
            color = f"rgb({int(90 + level * 145)},{int(110 + level * 115)},{int(106 + level * 52)})"
        box(fig, x1, y1, 0, x2 - x1, y2 - y1, 0.05, color, room,
            name=f"{ROOMS[room]['name']} · {power * 1000:.0f} W allocated")
        if room == selected:
            fig.add_trace(go.Scatter3d(x=[x1, x2, x2, x1, x1], y=[y1, y1, y2, y2, y1],
                z=[0.08] * 5, mode="lines", line=dict(color="#c8f48a", width=7),
                hoverinfo="skip", showlegend=False))
    # Back and left exterior walls; low front walls preserve the cutaway.
    for x, y, w, d, h in [(0, 9, 12, .16, 2.25), (-.12, 0, .12, 9, 1.65),
                            (0, -.12, 4.2, .12, .36), (5.6, -.12, 6.4, .12, .36),
                            (12, 0, .14, 4, .6)]:
        box(fig, x, y, .05, w, d, h, "#e3dfd1")
    # Partitions with actual openings between spaces.
    for x, y, w, d in [(0, 4.14, 2.8, .12), (3.8, 4.14, 4.3, .12),
                        (9.2, 4.14, 2.8, .12), (6.94, 0, .12, 2.6),
                        (6.94, 3.5, .12, .65), (4.44, 4.2, .12, 2.8),
                        (4.44, 8, .12, 1), (6.94, 4.2, .12, 2.9),
                        (6.94, 8.1, .12, .9)]:
        box(fig, x, y, .05, w, d, 1.1, "#d9d7cc")
    for x in (0.7, 2.8, 7.8, 10.2):
        box(fig, x, 8.94, .85, 1.1, .18, 1.05, "#86b6bc", opacity=.78)
        box(fig, x + .53, 8.91, .85, .045, .22, 1.05, "#e8e7dd")
    # Living room: woven rug, sofa, armchair, coffee table and media console.
    box(fig, 1.15, .65, .06, 4.55, 2.8, .035, "#d5cbb4", "living")
    box(fig, 1.4, 2.9, .15, 3.6, .85, .43, "#526e64", "living")
    box(fig, 1.4, 3.55, .4, 3.6, .22, .55, "#526e64", "living")
    for x in (1.4, 4.8):
        box(fig, x, 2.9, .3, .2, .85, .45, "#628374", "living")
    for x in (1.7, 2.7, 3.7):
        box(fig, x, 3.05, .58, .9, .52, .12, "#91a590", "living")
    box(fig, 5.35, 1.5, .17, .8, .9, .5, "#ab987c", "living")
    box(fig, 2.5, 1.45, .25, 1.7, .75, .18, "#a18f73", "living")
    box(fig, 3.0, 1.65, .44, .38, .28, .04, "#dde2d0", "living")
    box(fig, .7, .05, .08, 3.5, .4, .38, "#8a806f", "living")
    box(fig, 1.25, .2, .5, 2.3, .08, 1.05, "#202e32", "living")
    # Kitchen cabinetry, hob, sink and island stools.
    box(fig, 7.3, .15, .05, 4.4, .65, .78, "#6b8078", "kitchen")
    box(fig, 11.05, .8, .05, .65, 2.9, .78, "#6b8078", "kitchen")
    box(fig, 7.3, .15, .84, 4.4, .65, .07, "#e0dfd2", "kitchen")
    box(fig, 11.05, .8, .84, .65, 2.9, .07, "#e0dfd2", "kitchen")
    box(fig, 8.1, .28, .92, .85, .42, .02, "#26373b", "kitchen")
    for x in (8.25, 8.65):
        for y in (.35, .57):
            box(fig, x, y, .95, .17, .12, .015, "#758487", "kitchen")
    box(fig, 11.12, 1.25, .92, .48, .65, .015, "#8eaaad", "kitchen")
    box(fig, 7.3, 2.7, .05, .85, .8, 1.8, "#bbc6c2", "kitchen", name="Refrigerator · always-on")
    box(fig, 8.7, 2.0, .05, 1.6, .9, .85, "#a99b81", "kitchen")
    box(fig, 8.55, 1.9, .9, 1.9, 1.1, .08, "#e2ddce", "kitchen")
    for x in (8.85, 9.65):
        box(fig, x, 3.2, .1, .4, .4, .5, "#758a79", "kitchen")
    # Bedroom.
    box(fig, .65, 5.7, .06, 3.1, 2.8, .035, "#a0adb3", "bedroom")
    box(fig, 1.2, 6, .1, 2.15, 2.6, .38, "#a3947d", "bedroom")
    box(fig, 1.15, 8.55, .1, 2.25, .15, 1.0, "#aa9f8d", "bedroom")
    box(fig, 1.22, 6.03, .5, 2.1, 2.45, .18, "#e3e4d8", "bedroom")
    box(fig, 1.22, 6.05, .69, 2.1, 1.4, .05, "#788f9a", "bedroom")
    for x in (1.4, 2.5):
        box(fig, x, 7.85, .7, .65, .45, .12, "#f1ecdd", "bedroom")
    box(fig, .3, 8.0, .1, .65, .65, .55, "#9d917e", "bedroom")
    # Bathroom: bathtub, vanity, mirror and WC.
    box(fig, 4.7, 6.7, .05, .85, 1.9, .5, "#e8ece3", "bathroom")
    box(fig, 4.8, 6.85, .56, .64, 1.55, .02, "#a4c6c6", "bathroom")
    box(fig, 5.9, 8.0, .05, .85, .65, .8, "#8a9e97", "bathroom")
    box(fig, 6, 8.05, .87, .65, .5, .04, "#e3e9df", "bathroom")
    box(fig, 6, 8.95, 1.05, .7, .03, .85, "#a3bec0", "bathroom")
    box(fig, 5.95, 5.1, .05, .6, .85, .44, "#e1e7df", "bathroom")
    # Office with desk, monitor, chair, shelving.
    box(fig, 8, 7.6, .75, 2.8, .85, .12, "#b1a184", "office")
    for x in (8.1, 10.5):
        box(fig, x, 7.7, .05, .12, .65, .7, "#4d6060", "office")
    box(fig, 8.85, 8.0, .9, 1.05, .08, .65, "#203139", "office")
    box(fig, 8.95, 8.03, .98, .85, .03, .45, "#76c6c0", "office")
    box(fig, 8.9, 6.6, .2, .75, .75, .45, "#53796e", "office")
    box(fig, 8.9, 6.55, .6, .75, .1, .6, "#53796e", "office")
    box(fig, 11.25, 5, .05, .45, 3, 1.2, "#ad9d7e", "office")
    for y in (5.15, 5.6, 6.05, 6.5, 7):
        box(fig, 11.25, y, .85, .4, .22, .3, "#829e91", "office")
    # Garage + EV. Solar canopy is set back, leaving the vehicle visible.
    box(fig, 12, 9, .05, 4, .15, 1.6, "#abb7ac", "garage")
    box(fig, 12.1, 7.9, 1.95, 3.8, 1.0, .12, "#5d706b", "garage")
    for x in (12.3, 13.45, 14.6):
        box(fig, x, 7.98, 2.1, 1.0, .8, .05, "#28556a" if day.state["solar"] else "#586365", "garage", name="5.2 kWp solar array · illustrative")
    box(fig, 12.8, 4.55, .25, 1.9, 2.7, .55, "#dce7dc", "garage")
    box(fig, 12.95, 5.25, .82, 1.6, 1.25, .5, "#799da1", "garage")
    for x in (12.65, 14.65):
        for y in (4.95, 6.55):
            box(fig, x, y, .13, .2, .5, .43, "#29383a", "garage")
    box(fig, 15.3, 7.1, .3, .4, .45, 1.15, "#8ba58f", "garage", name="EV charger")
    box(fig, 15.1, 8.4, .15, .65, .35, 1.2, "#c0cebd", "garage", name="10 kWh battery")
    # Plantings and stepping stones give the house a landscaped base.
    for x, y in [(-.6, -.3), (-.6, 6), (16.4, 9), (16.4, 3.6)]:
        box(fig, x, y, -.1, .2, .2, 1.0, "#81735c")
        fig.add_trace(go.Scatter3d(x=[x + .1], y=[y + .1], z=[1.25], mode="markers",
            marker=dict(size=20, color="#5c8669", opacity=1), hoverinfo="skip", showlegend=False))
    for y in (-.7, -.35):
        box(fig, 4.4, y, -.16, 1, .25, .05, "#9eac9e")
    for room, info in ROOMS.items():
        x, y = info["xy"]
        power = room_power(day, room, index)
        fig.add_trace(go.Scatter3d(x=[x], y=[y], z=[1.95], mode="markers+text",
            marker=dict(size=5, color="#c7f28a" if day.state["lights"][room] > 0 else "#748681"),
            text=[f"{info['name']}<br>{power * 1000:.0f} W"], textposition="top center",
            textfont=dict(size=11, color="#f2f5e9"), customdata=[room],
            hovertemplate=f"{info['name']} · {info['area']:.1f} m²<br>Click to inspect<extra></extra>",
            showlegend=False))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0), showlegend=False, uirevision="house-camera",
        scene=dict(bgcolor="rgba(0,0,0,0)", aspectmode="manual", aspectratio=dict(x=1.7, y=1, z=.42),
            camera=dict(eye=dict(x=1.02, y=-1.23, z=1.16), center=dict(x=0, y=0, z=-.03)),
            xaxis=dict(visible=False, range=[-1.3, 17]), yaxis=dict(visible=False, range=[-1.3, 10]),
            zaxis=dict(visible=False, range=[-.5, 3.6])),
        font=dict(family="Segoe UI, sans-serif", color="#e6eede"), height=445)
    return fig

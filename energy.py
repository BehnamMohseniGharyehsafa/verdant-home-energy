"""Deterministic quarter-hour energy model. All quantities have explicit units.

This is a demonstrator, not a meter feed, building-physics solver or billing engine.
The reference and scenario use the same weather, PV and tariff assumptions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
import json
import math

import numpy as np

DT = 0.25  # hours per interval
HOURS = np.arange(96, dtype=float) * DT
ROOMS = {
    "living": {"name": "Living room", "area": 29.4, "lights_w": 84, "xy": (3.5, 2.1)},
    "kitchen": {"name": "Kitchen", "area": 21.0, "lights_w": 64, "xy": (9.5, 2.1)},
    "bedroom": {"name": "Bedroom", "area": 21.6, "lights_w": 48, "xy": (2.25, 6.6)},
    "bathroom": {"name": "Bathroom", "area": 12.0, "lights_w": 32, "xy": (5.75, 6.6)},
    "office": {"name": "Office", "area": 24.0, "lights_w": 40, "xy": (9.5, 6.6)},
    "garage": {"name": "Garage", "area": 20.0, "lights_w": 28, "xy": (14.0, 6.5)},
}

DEVICES = {
    "washer": {"name": "Washing machine", "room": "kitchen", "icon": "washer", "watts": 1800,
               "start": 17.0, "profile": [1.8, 0.3, 0.3, 0.3, 0.2, 0.2, 0.5, 0.4], "flex": True,
               "description": "2 h cycle · 1.00 kWh"},
    "dishwasher": {"name": "Dishwasher", "room": "kitchen", "icon": "appliance", "watts": 1600,
                   "start": 18.0, "profile": [1.6, 0.2, 0.2, 1.2, 0.2, 0.2], "flex": True,
                   "description": "1.5 h cycle · 0.90 kWh"},
    "water": {"name": "Water heater", "room": "bathroom", "icon": "water", "watts": 2000,
              "start": 17.0, "profile": [2.0] * 4, "flex": True,
              "description": "1 h heating window · 2.00 kWh"},
    "ev": {"name": "EV charger", "room": "garage", "icon": "car", "watts": 3600,
           "start": 18.0, "profile": [3.6] * 12, "flex": True,
           "description": "3 h charge · 10.80 kWh"},
    "oven": {"name": "Electric oven", "room": "kitchen", "icon": "appliance", "watts": 2200,
             "start": 18.0, "profile": [2.2, 1.2, 1.2, 1.2], "flex": False,
             "description": "1 h cooking window · 1.45 kWh"},
    "office": {"name": "Office workstation", "room": "office", "icon": "monitor", "watts": 140,
               "start": 9.0, "profile": [0.14] * 32, "flex": False,
               "description": "09:00–17:00 · 1.12 kWh"},
}

DEFAULT = {
    "lights": {room: 65 for room in ROOMS},
    "devices": {"washer": True, "dishwasher": True, "water": True, "ev": False,
                "oven": True, "office": True},
    "temperature": 21.0, "hvac": "heat", "solar": True, "battery": True,
    "optimize": False, "dr": False, "offpeak": 0.16, "day": 0.28,
    "peak": 0.42, "export_rate": 0.12, "carbon": 0.23, "standing": 0.65,
}


def default_state():
    return json.loads(json.dumps(DEFAULT))


def sanitize(raw):
    """Bound browser-supplied parameters before any calculation."""
    state = default_state()
    if not isinstance(raw, dict):
        return state
    for key in ("lights", "devices"):
        values = raw.get(key, {})
        if isinstance(values, dict):
            for item, default in state[key].items():
                try:
                    val = values.get(item, default)
                    if key == "lights":
                        val = float(val)
                        state[key][item] = min(100, max(0, val)) if math.isfinite(val) else default
                    else:
                        state[key][item] = bool(val)
                except (TypeError, ValueError):
                    pass
    for key, lower, upper in (("temperature", 16, 26), ("offpeak", 0, 2), ("day", 0, 2),
                               ("peak", 0, 2), ("export_rate", 0, 1), ("carbon", 0, 1),
                               ("standing", 0, 5)):
        try:
            val = float(raw.get(key, state[key]))
            if math.isfinite(val):
                state[key] = min(upper, max(lower, val))
        except (TypeError, ValueError):
            pass
    for key in ("solar", "battery", "optimize", "dr"):
        state[key] = bool(raw.get(key, state[key]))
    if raw.get("hvac") in ("heat", "cool", "off"):
        state["hvac"] = raw["hvac"]
    return state


def tariff(state):
    # Illustrative time-of-use tariff, not a named supplier offer.
    return np.where(HOURS < 7, state["offpeak"],
                    np.where((HOURS >= 17) & (HOURS < 19), state["peak"], state["day"]))


def time_label(slot):
    minutes = int(slot * 15)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def best_start(profile, prices, avoid_event=False):
    """Exhaustive contiguous-cycle search; ties prefer the earliest start.

    Every allowed cycle finishes in this 24-hour horizon. This optimizes only
    import-tariff cost of each appliance, not whole-home net cost or comfort.
    """
    candidates = []
    for start in range(97 - len(profile)):
        stop = start + len(profile)
        if avoid_event and start < 76 and stop > 68:
            continue
        cost = float(np.dot(profile, prices[start:stop]) * DT)
        candidates.append((cost, start))
    return min(candidates, key=lambda pair: (round(pair[0], 8), pair[1]))[1]


@dataclass
class Day:
    state: dict
    outdoor: np.ndarray
    loads: dict
    room_lights: dict
    schedules: dict
    load: np.ndarray
    pv: np.ndarray
    charge: np.ndarray
    discharge: np.ndarray
    soc: np.ndarray
    grid_in: np.ndarray
    grid_out: np.ndarray
    prices: np.ndarray
    interval_cost: np.ndarray

    @property
    def totals(self):
        used = float(self.load.sum() * DT)
        solar = float(self.pv.sum() * DT)
        exported = float(self.grid_out.sum() * DT)
        imports = float(self.grid_in.sum() * DT)
        return {
            "load": used, "solar": solar, "import": imports, "export": exported,
            "cost": float(self.interval_cost.sum()) + self.state["standing"],
            "carbon": imports * self.state["carbon"],
            "solar_self_consumption": 100 * (solar - exported) / solar if solar > 0 else 0,
            # Import displacement can include energy initially stored in the battery.
            "self_sufficiency": 100 * max(0, 1 - imports / used) if used > 0 else 0,
            "peak": float(self.grid_in.max()),
        }


def simulate(raw, day_offset=0):
    state = sanitize(raw)
    prices = tariff(state)
    # Synthetic autumn day. Offset adds reproducible weather/load variety.
    outdoor = 12 + 3.5 * np.sin((HOURS - 9) / 24 * 2 * np.pi) + 0.7 * math.sin(day_offset * 1.7)
    sun = np.maximum(0, np.sin((HOURS - 7.5) / 11 * np.pi))
    sun[(HOURS < 7.5) | (HOURS > 18.5)] = 0
    cloud = (0.82 + 0.12 * np.sin(HOURS * 1.3 + day_offset))
    pv = 5.2 * sun * cloud * (0.52 + 0.08 * math.cos(day_offset)) if state["solar"] else np.zeros(96)
    event = (HOURS >= 17) & (HOURS < 19)
    daylight_dimming = np.where((HOURS >= 8) & (HOURS < 17), 0.3, 1.0)
    room_lights = {}
    for room, info in ROOMS.items():
        light = info["lights_w"] / 1000 * state["lights"][room] / 100 * daylight_dimming
        room_lights[room] = light * np.where(event & state["dr"], 0.5, 1)
    lighting = np.sum(list(room_lights.values()), axis=0)
    # Quasi-steady heat balance; no claim to simulate measured indoor temperature.
    setpoint = np.full(96, state["temperature"], dtype=float)
    if state["dr"]:
        setpoint[event] += -1 if state["hvac"] == "heat" else 1
    passive_gain = 1.5 + 0.6 * sun
    if state["hvac"] == "heat":
        hvac = np.maximum(0, setpoint - outdoor - passive_gain) * 0.18 / 3.5
    elif state["hvac"] == "cool":
        hvac = np.maximum(0, outdoor + passive_gain - setpoint) * 0.18 / 3.2
    else:
        hvac = np.zeros(96)
    baseload = np.full(96, 0.11)  # fridge/router/standby, not remotely switched
    appliances = np.zeros(96)
    schedules = {}
    for key, device in DEVICES.items():
        profile = np.array(device["profile"])
        start = int(device["start"] * 4)
        if device["flex"] and (state["optimize"] or state["dr"]):
            start = best_start(profile, prices, avoid_event=state["dr"])
        power = np.zeros(96)
        if state["devices"][key]:
            power[start:start + len(profile)] = profile
        schedules[key] = {"start": start, "end": start + len(profile), "power": power,
                          "energy": float(power.sum() * DT)}
        appliances += power
    load = lighting + hvac + baseload + appliances
    charge, discharge, grid_in, grid_out = [np.zeros(96) for _ in range(4)]
    soc = np.zeros(97)
    soc[0] = 5.0 if state["battery"] else 0
    efficiency = math.sqrt(0.9)  # 90% round-trip efficiency; AC-side power arrays
    for i in range(96):
        net = load[i] - pv[i]
        soc[i + 1] = soc[i]
        if state["battery"]:
            if net < 0:
                charge[i] = min(-net, 2.5, (10 - soc[i]) / (DT * efficiency))
            else:
                discharge[i] = min(net, 2.5, max(0, soc[i] - 2) * efficiency / DT)
            soc[i + 1] += charge[i] * DT * efficiency - discharge[i] * DT / efficiency
        net += charge[i] - discharge[i]
        grid_in[i], grid_out[i] = max(net, 0), max(-net, 0)
    interval_cost = (grid_in * prices - grid_out * state["export_rate"]) * DT
    return Day(state, outdoor, {"Heating & cooling": hvac, "Lighting": lighting,
               "Appliances": appliances, "Always-on": baseload}, room_lights, schedules,
               load, pv, charge, discharge, soc, grid_in, grid_out, prices, interval_cost)


def reference_state(state):
    """Fixed declared reference; preserve scenario weather/tariffs/solar availability."""
    ref = sanitize(state)
    ref.update(temperature=22.0, hvac="heat", battery=False, optimize=False, dr=False)
    ref["lights"] = {room: 80 for room in ROOMS}
    ref["devices"] = default_state()["devices"]
    return ref


@lru_cache(maxsize=32)
def evaluate(serialized, day_offset=0):
    state = sanitize(json.loads(serialized))
    scenario = simulate(state, day_offset)
    reference = simulate(reference_state(state), day_offset)
    no_event = dict(state, dr=False)
    counterfactual = simulate(no_event, day_offset)
    event = (HOURS >= 17) & (HOURS < 19)
    reduction = max(0, float((counterfactual.grid_in[event] - scenario.grid_in[event]).sum() * DT))
    reward = reduction * 0.35 if state["dr"] else 0.0
    return scenario, reference, {"reduction": reduction if state["dr"] else 0.0,
                                 "reward": reward, "counterfactual": counterfactual}


def evaluate_state(state, day_offset=0):
    return evaluate(json.dumps(sanitize(state), sort_keys=True), day_offset)


def history(state, count, end_date):
    rows = []
    for offset in range(-count + 1, 1):
        scenario, ref, event = evaluate_state(state, offset)
        a, b = scenario.totals, ref.totals
        rows.append({"date": (end_date + timedelta(days=offset)).isoformat(), **a,
                     "reference_cost": b["cost"], "reference_load": b["load"],
                     "reference_carbon": b["carbon"], "reward": event["reward"],
                     "saving": b["cost"] - a["cost"] + event["reward"]})
    return rows


def room_power(day, room, index):
    info = ROOMS[room]
    total_area = sum(r["area"] for r in ROOMS.values())
    power = day.room_lights[room][index] + day.loads["Heating & cooling"][index] * info["area"] / total_area
    for key, device in DEVICES.items():
        if device["room"] == room:
            power += day.schedules[key]["power"][index]
    # Allocate always-on load explicitly so room allocations reconcile to whole home.
    power += day.loads["Always-on"][index] * info["area"] / total_area
    return float(power)

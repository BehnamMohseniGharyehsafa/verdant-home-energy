"""Clock-driven, session-local simulation. No device telemetry is fabricated.

The daily scenario model remains a separate, explicitly labelled projection.
This runtime integrates room thermal mass and battery state over model time.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import math

import numpy as np
from energy import DEVICES, ROOMS, evaluate_state, sanitize

IRELAND = ZoneInfo("Europe/Dublin")
TOTAL_AREA = sum(room["area"] for room in ROOMS.values())
MODES = {"irish", "play", "manual"}


def irish_now(now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("The clock requires a timezone-aware datetime")
    return now.astimezone(IRELAND)


def sample(values, seconds):
    """Interpolate continuous profiles without mixing the next model day."""
    x = min(95, max(0, seconds / 900))
    return float(np.interp(x, np.arange(96), values))


def control_state(overrides):
    raw = overrides if isinstance(overrides, dict) else {}
    return {key: raw.get(key, "auto") if raw.get(key) in ("auto", "on", "off") else "auto"
            for key in DEVICES}


def step(raw, previous=None, mode="irish", manual_slot=57, overrides=None, now=None):
    state = sanitize(raw)
    previous = previous if isinstance(previous, dict) else {}
    local = irish_now(now)
    stamp = local.timestamp()
    mode = mode if mode in MODES else "irish"
    raw_elapsed = max(0, stamp - float(previous.get("stamp", stamp)))
    elapsed = min(60, raw_elapsed)
    changed = previous.get("mode") != mode
    local_seconds = local.hour * 3600 + local.minute * 60 + local.second + local.microsecond / 1e6
    if mode == "irish":
        seconds = local_seconds
        dt = elapsed
    elif mode == "play":
        seconds = float(previous.get("seconds", local_seconds)) + (0 if changed else elapsed * 300)
        dt = 0 if changed else elapsed * 300
    else:
        seconds = max(0, min(95, float(manual_slot or 0))) * 900
        dt = elapsed  # fixed outdoor/time conditions; physical state continues to evolve
    wrapped = seconds >= 86400
    seconds %= 86400
    jumped = changed or wrapped or raw_elapsed > 60 or (mode == "manual" and abs(seconds - previous.get("seconds", seconds)) > 1)
    if mode == "irish" and previous.get("date") != local.date().isoformat():
        jumped = True
    if jumped:
        dt = 0
    day, _, _ = evaluate_state(state)
    index = min(95, int(seconds // 900))
    outdoor = sample(day.outdoor, seconds)
    room_temps = previous.get("temperatures", {}) if not jumped else {}
    temperatures = {key: float(room_temps.get(key, state["temperature"] - .6 + i * .07))
                    for i, key in enumerate(ROOMS)}
    overrides = control_state(overrides)
    appliance_power = {}
    for key, device in DEVICES.items():
        action = overrides[key]
        if action == "on":
            appliance_power[key] = device["watts"] / 1000
        elif action == "off":
            appliance_power[key] = 0.0
        else:
            # Daily appliance stages have exact quarter-hour boundaries.
            appliance_power[key] = float(day.schedules[key]["power"][index])
    event = state["dr"] and 17 * 3600 <= seconds < 19 * 3600
    target = state["temperature"] + ((-1 if state["hvac"] == "heat" else 1) if event else 0)
    average = sum(temperatures[k] * ROOMS[k]["area"] for k in ROOMS) / TOTAL_AREA
    base_hvac = sample(day.loads["Heating & cooling"], seconds)
    if state["hvac"] == "heat":
        hvac = min(3.0, max(0, base_hvac + .7 * (target - average)))
        thermal = hvac * 3.5
    elif state["hvac"] == "cool":
        hvac = min(3.0, max(0, base_hvac + .7 * (average - target)))
        thermal = -hvac * 3.2
    else:
        hvac = thermal = 0.0
    lights = {key: float(day.room_lights[key][index]) for key in ROOMS}
    pv = sample(day.pv, seconds)
    # Small deterministic cloud variation; zero at night and when PV is disabled.
    pv *= 1 + .035 * math.sin(seconds / 73) + .018 * math.sin(seconds / 29)
    pv = min(5.2, max(0, pv))
    baseload = .11 * (1 + .025 * math.sin(seconds / 41))
    power = sum(lights.values()) + sum(appliance_power.values()) + hvac + baseload
    soc = float(previous.get("soc", day.soc[index])) if not jumped else float(day.soc[index])
    if not state["battery"]:
        soc = 0.0
    elif not previous.get("battery_enabled", state["battery"]):
        soc = float(day.soc[index])
    eta = math.sqrt(.9)
    hours = dt / 3600
    limit_hours = max(hours, 1 / 3600)
    charge = discharge = 0.0
    surplus = pv - power
    if state["battery"]:
        soc = max(2, min(10, soc))
        if surplus > 0:
            charge = min(surplus, 2.5, (10 - soc) / (limit_hours * eta))
        else:
            discharge = min(-surplus, 2.5, (soc - 2) * eta / limit_hours)
        soc += (charge * eta - discharge / eta) * hours
    net = power + charge - pv - discharge
    imports, exports = max(0, net), max(0, -net)
    room_power = {}
    for key, info in ROOMS.items():
        share = info["area"] / TOTAL_AREA
        appliance_heat = sum(value for dev, value in appliance_power.items() if DEVICES[dev]["room"] == key)
        room_power[key] = lights[key] + appliance_heat + (hvac + baseload) * share
        # RC heat balance: C=0.08 kWh/K per m²; UA shares sum to 0.18 kW/K.
        internal_gain = .12 * share + .8 * (appliance_heat + lights[key])
        solar_gain = pv * .18 * share
        loss = .18 * share * (temperatures[key] - outdoor)
        temperatures[key] += (thermal * share + internal_gain + solar_gain - loss) * hours / (info["area"] * .08)
    session = previous.get("session", {}) if not jumped else {}
    price = float(day.prices[index])
    session = {"energy": float(session.get("energy", 0)) + power * hours,
               "cost": float(session.get("cost", 0)) + (imports * price - exports * state["export_rate"]) * hours,
               "carbon": float(session.get("carbon", 0)) + imports * state["carbon"] * hours,
               "hours": float(session.get("hours", 0)) + hours}
    history = previous.get("history", [])[-89:] if not jumped else []
    history = history + [{"time": f"{int(seconds)//3600:02d}:{int(seconds)%3600//60:02d}:{int(seconds)%60:02d}",
                           "home": power, "solar": pv, "grid": imports}]
    return {"stamp": stamp, "seconds": seconds, "mode": mode, "date": local.date().isoformat(),
            "index": index, "step_hours": hours, "local_iso": local.isoformat(),
            "home": power, "pv": pv, "charge": charge, "discharge": discharge,
            "import": imports, "export": exports, "soc": soc, "battery_enabled": state["battery"],
            "hvac": hvac, "outdoor": outdoor, "temperatures": temperatures, "room_power": room_power,
            "lights": lights, "appliances": appliance_power, "overrides": overrides,
            "price": price, "carbon_rate": imports * state["carbon"], "session": session,
            "history": history, "phase": (stamp % 8) / 8, "target": target,
            "lighting_levels": state["lights"], "solar_enabled": state["solar"], "hvac_mode": state["hvac"]}


def picked_object(info):
    """Only explicit, allowlisted clickable actors may change controls."""
    if not isinstance(info, dict):
        return None
    rep = info.get("representationId", "")
    if not isinstance(rep, str):
        return None
    bits = rep.split(":")
    if len(bits) != 3 or bits[0] not in ("home", "devices"):
        return None
    kind, key = bits[1:]
    if (kind == "light" and key in ROOMS) or (kind == "device" and key in DEVICES):
        return kind, key
    if kind == "room" and key in ROOMS:
        return kind, key
    return None

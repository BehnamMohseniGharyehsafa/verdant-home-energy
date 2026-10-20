"""Approximate solar clock for the illustrative Dublin residence.

NOAA fractional-year equations: https://gml.noaa.gov/grad/solcalc/solareqns.PDF
No location permission or weather API is used. The moon is a night symbol,
not an astronomical moon-position or phase prediction.
"""
from datetime import datetime, timedelta
from calendar import isleap
import math

LATITUDE, LONGITUDE = 53.3498, -6.2603


def solar_terms(local):
    hour = local.hour + local.minute / 60 + local.second / 3600
    gamma = 2 * math.pi / (366 if isleap(local.year) else 365) * (local.timetuple().tm_yday - 1 + (hour - 12) / 24)
    eq = 229.18 * (.000075 + .001868 * math.cos(gamma) - .032077 * math.sin(gamma)
                   - .014615 * math.cos(2 * gamma) - .040849 * math.sin(2 * gamma))
    dec = (.006918 - .399912 * math.cos(gamma) + .070257 * math.sin(gamma)
           - .006758 * math.cos(2 * gamma) + .000907 * math.sin(2 * gamma)
           - .002697 * math.cos(3 * gamma) + .00148 * math.sin(3 * gamma))
    return eq, dec


def sky_state(local, seconds=None):
    if local.tzinfo is None:
        raise ValueError("Solar calculations require an aware Irish local datetime")
    if seconds is not None:
        local = local.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(seconds=float(seconds) % 86400)
    eq, dec = solar_terms(local)
    latitude = math.radians(LATITUDE)
    offset = local.utcoffset().total_seconds() / 3600
    minutes = local.hour * 60 + local.minute + local.second / 60
    solar_minutes = (minutes + eq + 4 * LONGITUDE - 60 * offset) % 1440
    hour_angle = math.radians(solar_minutes / 4 - 180)
    cosine = math.sin(latitude) * math.sin(dec) + math.cos(latitude) * math.cos(dec) * math.cos(hour_angle)
    elevation = math.degrees(math.asin(max(-1, min(1, cosine))))
    # Conventional sunrise/sunset zenith, incorporating approximate refraction.
    noon = local.replace(hour=12, minute=0, second=0, microsecond=0)
    eq_noon, dec_noon = solar_terms(noon)
    argument = ((math.cos(math.radians(90.833)) - math.sin(latitude) * math.sin(dec_noon))
                / (math.cos(latitude) * math.cos(dec_noon)))
    half_day = math.degrees(math.acos(max(-1, min(1, argument)))) * 4
    solar_noon = 720 - 4 * LONGITUDE - eq_noon + 60 * offset
    fmt = lambda m: f"{int(round(m)) // 60 % 24:02d}:{int(round(m)) % 60:02d}"
    daylight = elevation >= -.833
    phase = "day" if elevation >= 6 else ("golden" if daylight else ("twilight" if elevation > -6 else "night"))
    colors = {"day": [.20, .34, .42], "golden": [.27, .27, .32],
              "twilight": [.10, .14, .25], "night": [.025, .045, .095]}
    return {"daylight": daylight, "street_on": not daylight, "phase": phase,
            "elevation": elevation, "sunrise": fmt(solar_noon - half_day), "sunset": fmt(solar_noon + half_day),
            "background": colors[phase], "orb": "sun" if daylight else "moon",
            "orb_left": 72 - 12 * math.sin(hour_angle), "local_time": local.strftime("%H:%M"),
            "date": local.date().isoformat(), "location": "Dublin · 53.35°N, 6.26°W"}

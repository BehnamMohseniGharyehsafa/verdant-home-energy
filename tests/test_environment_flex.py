from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pytest

from energy import default_state, evaluate_state, DEVICES
from environment import sky_state
from runtime import step
from flexibility import report, network_snapshot
from house_scene import scene_children, dynamic_values

IRELAND=ZoneInfo("Europe/Dublin")


def local(hour,month=10,day=20):
    return datetime(2026,month,day,hour,tzinfo=IRELAND)


def test_dublin_day_night_sunrise_and_streetlights():
    day=sky_state(local(13)); night=sky_state(local(21))
    assert day["daylight"] and day["orb"]=="sun" and not day["street_on"]
    assert not night["daylight"] and night["orb"]=="moon" and night["street_on"]
    # Independent seasonal sanity bounds for Dublin in late October (local IST).
    rise_h,rise_m=map(int,day["sunrise"].split(":"))
    set_h,set_m=map(int,day["sunset"].split(":"))
    assert 7*60+40 < rise_h*60+rise_m < 8*60+20
    assert 18*60 < set_h*60+set_m < 18*60+40
    assert sky_state(local(21),13*3600)["daylight"]


def test_solar_clock_tracks_irish_dst_and_seasons():
    minutes=lambda text:sum(int(v)*factor for v,factor in zip(text.split(":"),(60,1)))
    before=sky_state(local(12,10,24)); after=sky_state(local(12,10,25))
    assert 55 < minutes(before["sunrise"])-minutes(after["sunrise"]) < 65
    assert sky_state(local(20,6,20))["daylight"]
    assert not sky_state(local(20,12,20))["daylight"]
    with pytest.raises(ValueError):
        sky_state(datetime(2026,10,20,12))


def test_live_pv_zero_after_sunset_and_public_lights_outside_home_meter():
    state=default_state()
    snapshot=step(state,now=local(21))
    assert snapshot["pv"]==0 and snapshot["sky"]["street_on"]
    assert sum(snapshot["room_power"].values())==pytest.approx(snapshot["home"])
    values=dynamic_values(snapshot)
    assert values[-1][0]["visibility"] and values[-2][0]["visibility"]
    day_values=dynamic_values(step(state,now=local(13)))
    assert not day_values[-1][0]["visibility"]


def test_configurable_dr_preserves_cycles_and_reconciles_import_effects():
    state=default_state(); state.update(dr=True,dr_dim=75,dr_relief=1.5,dr_reward=.6,solar=False,battery=False)
    state["devices"]["ev"]=True
    result=report(state)
    assert result["event"]["reward"]==pytest.approx(result["event"]["reduction"]*.6)
    assert sum(result["impacts"].values())==pytest.approx(result["signed_delta"])
    assert result["event"]["reduction"]>0
    for row in result["rows"]:
        if DEVICES[row["key"]]["flex"]:
            assert row["shifted"]
            assert result["day"].schedules[row["key"]]["energy"]==pytest.approx(result["baseline"].schedules[row["key"]]["energy"])
    lighting_before=result["baseline"].loads["Lighting"][68:76]
    np.testing.assert_allclose(result["day"].loads["Lighting"][68:76],lighting_before*.25)


def test_zero_response_strategy_and_opt_out_do_not_create_rewards():
    state=default_state(); state.update(dr=True,dr_dim=0,dr_relief=0,dr_shift=False,dr_reward=1)
    result=report(state)
    assert result["signed_delta"]==pytest.approx(0)
    assert result["event"]["reward"]==0
    state.update(dr=False,dr_dim=80,dr_relief=2,dr_shift=True)
    assert report(state)["event"]["reward"]==0


def test_live_dr_and_network_preview_respect_different_declared_models():
    state=default_state(); state.update(dr=True,dr_relief=1.5,dr_dim=75)
    snapshot=step(state,overrides={"ev":"on"},now=local(18))
    assert snapshot["target"]==19.5
    no_response=step(dict(state,dr=False),now=local(18))
    assert snapshot["lights"]["living"]==pytest.approx(no_response["lights"]["living"]*.25)
    network=network_snapshot(state,snapshot)
    day=evaluate_state(state)[0]
    assert network["home"]==pytest.approx(day.load[72])
    assert network["appliances"]["ev"]==0
    assert snapshot["appliances"]["ev"]==3.6


def test_network_actor_identity_survives_envelope_and_daylight_changes():
    state=default_state()
    scenes=[scene_children("grid",mode,step(state,now=local(13 if mode=="exterior" else 21)))
            for mode in ("exterior","interior","xray")]
    assert all([actor.id for actor in scene]==[actor.id for actor in scenes[0]] for scene in scenes)
    assert scenes[0][-1].id=="grid-street-glow"


def test_actual_dash_strategy_inputs_reach_model_and_export():
    import csv,io
    from app import app,server,export_csv
    from energy import ROOMS
    metadata=app.callback_map["scenario.data"]
    state=default_state()
    lights=[{"type":"brightness","room":key} for key in ROOMS]
    devices=[{"type":"device-toggle","device":key} for key in DEVICES]
    values=[[65]*6,[["on"] if state["devices"][key] else [] for key in DEVICES],
        21,"heat",["on"],["on"],[],["on"],.16,.28,.42,.12,.65,.23,75,1.5,["on"],.6]
    response=server.test_client().post("/_dash-update-component",json={
        "output":"scenario.data","outputs":{"id":"scenario","property":"data"},
        "inputs":[{**item,"value":value} for item,value in zip(metadata["inputs"],values)],
        "state":[{**item,"value":value} for item,value in zip(metadata["state"],[lights,devices])],
        "changedPropIds":["dr-dim.value"]})
    assert response.status_code==200
    actual=response.get_json()["response"]["scenario"]["data"]
    assert actual["dr"] and actual["dr_dim"]==75 and actual["dr_relief"]==1.5 and actual["dr_reward"]==.6
    rows=list(csv.DictReader(io.StringIO(export_csv(actual))))
    assert all(row["dr_lighting_reduction_percent"]=="75.0" and row["dr_reward_eur_per_kwh"]=="0.6" for row in rows)

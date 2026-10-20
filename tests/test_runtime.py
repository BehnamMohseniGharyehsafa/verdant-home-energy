from datetime import datetime, timedelta, timezone
import json
import math

import numpy as np
import pytest

from energy import DEFAULT, DEVICES, ROOMS, default_state, evaluate_state
from runtime import irish_now, step, picked_object
from house_scene import batches, scene_children, scene_patch, dynamic_values


@pytest.mark.parametrize("utc,expected,abbreviation",[
    ("2026-01-20T12:00:00+00:00","12:00:00","GMT"),
    ("2026-07-20T12:00:00+00:00","13:00:00","IST"),
    ("2026-10-25T00:30:00+00:00","01:30:00","IST"),
    ("2026-10-25T01:30:00+00:00","01:30:00","GMT"),
])
def test_irish_clock_and_dst(utc,expected,abbreviation):
    local=irish_now(datetime.fromisoformat(utc))
    assert local.strftime("%H:%M:%S")==expected
    assert local.tzname()==abbreviation


def test_clock_modes_and_model_time():
    now=datetime(2026,10,20,12,0,tzinfo=timezone.utc)
    live=step(DEFAULT,now=now)
    assert live["seconds"]==13*3600
    play=step(DEFAULT,live,"play",now=now)
    after=step(DEFAULT,play,"play",now=now+timedelta(seconds=2))
    assert after["seconds"]-play["seconds"]==600
    assert after["step_hours"]==pytest.approx(600/3600)
    manual=step(DEFAULT,after,"manual",72,now=now+timedelta(seconds=3))
    assert manual["index"]==72 and manual["seconds"]==18*3600
    assert manual["session"]["energy"]==0


def test_live_override_changes_actual_power_without_changing_projection():
    now=datetime(2026,10,20,12,tzinfo=timezone.utc)
    state=default_state()
    baseline=evaluate_state(state)[0].totals["load"]
    auto=step(state,now=now)
    on=step(state,auto,overrides={"ev":"on"},now=now)
    off=step(state,on,overrides={"ev":"off"},now=now)
    assert auto["appliances"]["ev"]==0
    assert on["appliances"]["ev"]==3.6
    assert on["home"]-auto["home"]==pytest.approx(3.6)
    assert off["home"]==pytest.approx(auto["home"])
    assert evaluate_state(state)[0].totals["load"]==baseline


def test_live_light_switch_and_room_reconciliation():
    now=datetime(2026,10,20,19,tzinfo=timezone.utc)
    state=default_state()
    on=step(state,now=now)
    state["lights"]["living"]=0
    off=step(state,on,now=now)
    assert off["lights"]["living"]==0
    assert on["home"]-off["home"]==pytest.approx(on["lights"]["living"])
    assert sum(off["room_power"].values())==pytest.approx(off["home"])


@pytest.mark.parametrize("solar,battery",[(True,True),(True,False),(False,True),(False,False)])
def test_runtime_conserves_power_and_battery_energy(solar,battery):
    state=default_state()
    state.update(solar=solar,battery=battery)
    now=datetime(2026,10,20,10,tzinfo=timezone.utc)
    snapshot=step(state,mode="play",now=now)
    for tick in range(1,70):
        previous=snapshot
        snapshot=step(state,previous,"play",overrides={"ev":"on"},now=now+timedelta(seconds=tick*2))
        assert snapshot["pv"]+snapshot["discharge"]+snapshot["import"]==pytest.approx(snapshot["home"]+snapshot["charge"]+snapshot["export"])
        assert snapshot["import"]*snapshot["export"]==0
        assert snapshot["charge"]*snapshot["discharge"]==0
        assert max(snapshot["charge"],snapshot["discharge"])<=2.5
        if battery:
            assert 2-1e-9<=snapshot["soc"]<=10+1e-9
            if snapshot["step_hours"]>0:
                assert snapshot["soc"]-previous["soc"]==pytest.approx(snapshot["step_hours"]*(snapshot["charge"]*math.sqrt(.9)-snapshot["discharge"]/math.sqrt(.9)))
        else:
            assert snapshot["soc"]==0


def test_room_thermal_state_evolves_and_heating_affects_it():
    state=default_state()
    state["solar"]=False
    now=datetime(2026,10,20,3,tzinfo=timezone.utc)
    initial=step(state,mode="play",now=now)
    heated=step(state,initial,"play",now=now+timedelta(seconds=10))
    state["hvac"]="off"
    unheated=step(state,initial,"play",now=now+timedelta(seconds=10))
    assert heated["temperatures"]["living"]>unheated["temperatures"]["living"]
    assert heated["temperatures"]!=initial["temperatures"]
    assert unheated["hvac"]==0


def test_long_inactive_gap_resets_instead_of_fabricating_energy():
    now=datetime(2026,10,20,12,tzinfo=timezone.utc)
    before=step(DEFAULT,now=now)
    after=step(DEFAULT,before,now=now+timedelta(minutes=10))
    assert after["session"]["hours"]==0 and len(after["history"])==1


def test_only_known_3d_controls_are_actionable():
    assert picked_object({"representationId":"devices:light:kitchen"})==("light","kitchen")
    assert picked_object({"representationId":"home:device:ev"})==("device","ev")
    for bad in [None,{}, {"representationId":"outside:light:kitchen"},{"representationId":"home:device:unknown"}, {"representationId":"home-material-1"}]:
        assert picked_object(bad) is None


@pytest.mark.parametrize("mode",["exterior","interior","xray"])
def test_meshes_have_valid_geometry_and_unique_pick_ids(mode):
    for opacity,mesh in batches(mode).items():
        assert np.isfinite(mesh.points).all()
        assert len(mesh.normals)==len(mesh.points)==len(mesh.colors)
        size=len(mesh.points)//3
        for cells in (mesh.polys,mesh.lines):
            cursor=0
            while cursor<len(cells):
                count=cells[cursor]
                assert min(cells[cursor+1:cursor+1+count])>=0
                assert max(cells[cursor+1:cursor+1+count])<size
                cursor+=count+1
    actors=scene_children("devices",mode)
    ids=[actor.id for actor in actors]
    assert len(ids)==len(set(ids))
    assert all(f"devices:light:{key}" in ids for key in ROOMS)
    assert all(f"devices:device:{key}" in ids for key in DEVICES)
    # Dynamic updates do not replace/recreate the entire scene.
    patch=scene_patch("devices",mode,step(DEFAULT),False).to_plotly_json()
    assert all(op["operation"]=="Assign" for op in patch["operations"])
    assert len(patch["operations"])<10


def test_zoom_applies_to_the_whole_scene():
    scene=scene_children("home","exterior",zoom=2)
    assert scene[0].actor["scale"]==[2,2,2]
    for actor,properties in dynamic_values(step(DEFAULT),2):
        assert actor.get("scale",[2])[0]==2


def test_envelope_modes_preserve_actor_identity_and_order():
    # VTK must not dispose/reorder actors while a live patch or pick is pending.
    modes=[scene_children("home",mode) for mode in ("exterior","interior","xray")]
    assert all([actor.id for actor in scene]==[actor.id for actor in modes[0]] for scene in modes)
    for mode in ("exterior","interior","xray"):
        assert min(value for mesh in batches(mode).values() for value in mesh.points[2::3])>=-.35

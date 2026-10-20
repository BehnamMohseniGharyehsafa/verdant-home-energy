"""Send real Dash requests for 3D picks rather than calling UI helpers directly."""
import json

from app import app,server
from energy import ROOMS,DEVICES,DEFAULT
from runtime import step


def pick_request(rep,levels=None,overrides=None):
    levels=levels or [65]*len(ROOMS)
    key=next(key for key in app.callback_map if "control-feedback.children" in key)
    metadata=app.callback_map[key]
    light_ids=[{"type":"brightness","room":room} for room in ROOMS]
    outputs=[]
    for output in metadata["output"]:
        if isinstance(output.component_id,dict):
            outputs.append([{"id":item,"property":output.component_property} for item in light_ids])
        else:
            outputs.append({"id":output.component_id,"property":output.component_property})
    values=["Home",{"representationId":rep},None,[0]*len(ROOMS),[0]*len(DEVICES),0]
    states=[light_ids,levels,overrides or {},step(DEFAULT)]
    return server.test_client().post("/_dash-update-component",json={"output":key,"outputs":outputs,
        "inputs":[{**item,"value":value} for item,value in zip(metadata["inputs"],values)],
        "state":[{**item,"value":value} for item,value in zip(metadata["state"],states)],
        "changedPropIds":["home-scene.clickInfo"]})


def test_3d_light_pick_changes_slider_and_can_be_clicked_again():
    response=pick_request("home:light:living",[35]*len(ROOMS))
    assert response.status_code==200
    data=response.get_json()["response"]
    room_id=json.dumps({"room":"living","type":"brightness"},sort_keys=True,separators=(",",":"))
    assert data[room_id]["value"]==0
    assert data["home-scene"]["clickInfo"] is None
    assert data["devices-scene"]["clickInfo"] is None
    overrides=data["device-overrides"]["data"]
    response=pick_request("home:light:living",[0]+[35]*(len(ROOMS)-1),overrides)
    assert response.status_code==200
    assert response.get_json()["response"][room_id]["value"]==35


def test_3d_ev_pick_creates_live_override():
    response=pick_request("devices:device:ev")
    assert response.status_code==200
    assert response.get_json()["response"]["device-overrides"]["data"]["ev"]=="on"


def test_non_control_surfaces_do_not_change_devices():
    assert pick_request("home-material-0").status_code==204

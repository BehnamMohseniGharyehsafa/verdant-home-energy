"""Matched demand-response reporting and schedule-based network preview."""
import numpy as np
from energy import DEVICES, DT, evaluate_state, sanitize, time_label


def report(raw, index=70):
    state=sanitize(raw)
    day,_,event=evaluate_state(state)
    baseline=event["counterfactual"]
    window=slice(68,76)
    before=float(baseline.grid_in[window].sum()*DT)
    after=float(day.grid_in[window].sum()*DT)
    rows=[]
    for key,device in DEVICES.items():
        a,b=baseline.schedules[key],day.schedules[key]
        rows.append({"key":key,"name":device["name"],"enabled":state["devices"][key],
            "before":f"{time_label(a['start'])}–{time_label(a['end'])}",
            "after":f"{time_label(b['start'])}–{time_label(b['end'])}",
            "shifted":a["start"]!=b["start"], "flexible":device["flex"],
            "event_delta":float((a["power"][window]-b["power"][window]).sum()*DT),
            "energy":b["energy"]})
    impacts={name:float((baseline.loads[name][window]-day.loads[name][window]).sum()*DT)
             for name in ("Appliances","Lighting","Heating & cooling")}
    signed=before-after
    impacts["Storage interaction"]=signed-sum(impacts.values())
    return {"state":state,"day":day,"baseline":baseline,"event":event,"rows":rows,"impacts":impacts,
            "before_kwh":before,"after_kwh":after,"signed_delta":signed,
            "before_peak":float(np.max(baseline.grid_in[window])),"after_peak":float(np.max(day.grid_in[window])),
            "bill_delta":baseline.totals["cost"]-day.totals["cost"],
            "event_carbon_delta":signed*state["carbon"],"index":max(0,min(95,int(index or 0)))}


def network_snapshot(raw, live):
    """Use the daily projection for the DR comparison, without live overrides."""
    state=sanitize(raw)
    day,_,_=evaluate_state(state)
    live=live or {}
    i=max(0,min(95,int(live.get("index",70))))
    return {**live,"home":float(day.load[i]),"pv":float(day.pv[i]),
            "import":float(day.grid_in[i]),"export":float(day.grid_out[i]),
            "charge":float(day.charge[i]),"discharge":float(day.discharge[i]),"soc":float(day.soc[i]),
            "battery_enabled":state["battery"],"lighting_levels":state["lights"],
            "appliances":{key:float(day.schedules[key]["power"][i]) for key in DEVICES},
            "dr_active":state["dr"] and 68<=i<76,"dr_dim":state["dr_dim"]}

"""Accounting and behavior checks, independent of visual implementation."""
import csv
import io
import json

import numpy as np
import pytest

from energy import (DT, DEVICES, ROOMS, default_state, simulate, evaluate_state,
                    room_power, best_start, sanitize, tariff)


@pytest.mark.parametrize("solar,battery,dr", [(True, True, False), (True, True, True),
    (False, True, True), (True, False, False), (False, False, False)])
def test_energy_conservation(solar, battery, dr):
    state = default_state()
    state.update(solar=solar, battery=battery, dr=dr)
    state["devices"]["ev"] = True
    day = simulate(state)
    np.testing.assert_allclose(day.pv + day.discharge + day.grid_in,
                               day.load + day.charge + day.grid_out, atol=1e-12)
    assert np.all(day.grid_in >= 0) and np.all(day.grid_out >= 0)
    assert np.all(day.grid_in * day.grid_out == 0)
    assert np.all(day.charge * day.discharge == 0)
    if battery:
        eta = np.sqrt(.9)
        np.testing.assert_allclose(np.diff(day.soc), DT * (day.charge * eta - day.discharge / eta), atol=1e-12)
        assert day.soc.min() >= 2 - 1e-10 and day.soc.max() <= 10 + 1e-10
        assert day.charge.max() <= 2.5 and day.discharge.max() <= 2.5
    else:
        assert np.all(day.soc == 0)


def test_cost_and_carbon_hand_calculation():
    state = default_state()
    state.update(solar=False, battery=False, hvac="off", carbon=.25, standing=.65,
                 offpeak=.10, day=.20, peak=.40)
    state["lights"] = {key: 0 for key in ROOMS}
    state["devices"] = {key: False for key in DEVICES}
    day = simulate(state)
    # 110 W for 24 h; 7 off-peak, 15 day, 2 peak hours.
    assert day.totals["load"] == pytest.approx(.11 * 24)
    assert day.totals["cost"] == pytest.approx(.11 * (7 * .1 + 15 * .2 + 2 * .4) + .65)
    assert day.totals["carbon"] == pytest.approx(.11 * 24 * .25)


def test_room_allocation_reconciles():
    day = simulate(default_state())
    for index in range(96):
        assert sum(room_power(day, r, index) for r in ROOMS) == pytest.approx(day.load[index])


def test_tariff_boundaries():
    values = tariff(default_state())
    assert values[27] == .16 and values[28] == .28
    assert values[67] == .28 and values[68] == .42
    assert values[75] == .42 and values[76] == .28


def test_cycle_optimizer_is_global_tariff_minimum_and_preserves_energy():
    original = default_state()
    optimized = default_state()
    original["devices"]["ev"] = optimized["devices"]["ev"] = True
    optimized["optimize"] = True
    before, after = simulate(original), simulate(optimized)
    for key, device in DEVICES.items():
        assert after.schedules[key]["energy"] == pytest.approx(before.schedules[key]["energy"])
        if device["flex"]:
            profile = np.array(device["profile"])
            start = after.schedules[key]["start"]
            selected_cost = np.dot(profile, after.prices[start:start + len(profile)]) * DT
            for alternative in range(97 - len(profile)):
                assert selected_cost <= np.dot(profile, after.prices[alternative:alternative + len(profile)]) * DT + 1e-10


def test_demand_response_matches_counterfactual_and_avoids_peak_cycles():
    state = default_state()
    state.update(dr=True, battery=False, solar=False)
    day, _, event = evaluate_state(state)
    expected = max(0, float((event["counterfactual"].grid_in[68:76] - day.grid_in[68:76]).sum() * DT))
    assert event["reduction"] == pytest.approx(expected)
    assert event["reward"] == pytest.approx(expected * .35)
    assert expected > 0
    for key, item in DEVICES.items():
        if item["flex"]:
            assert not day.schedules[key]["power"][68:76].any()
            assert day.schedules[key]["energy"] == pytest.approx(event["counterfactual"].schedules[key]["energy"])


def test_no_event_no_reward():
    _, _, event = evaluate_state(default_state())
    assert event["reward"] == 0 and event["reduction"] == 0


def test_thermostat_and_light_controls_reduce_demand():
    state = default_state()
    before = simulate(state)
    state["temperature"] = 19
    state["lights"] = {key: 0 for key in ROOMS}
    after = simulate(state)
    assert after.totals["load"] < before.totals["load"]
    assert after.loads["Lighting"].sum() == 0
    state["hvac"] = "off"
    assert simulate(state).loads["Heating & cooling"].sum() == 0


def test_invalid_input_is_bounded():
    state = sanitize({"temperature": float("nan"), "carbon": -2, "peak": 100,
                      "lights": {"living": -30}, "offpeak": None, "hvac": "invalid"})
    assert state["temperature"] == 21 and state["carbon"] == 0
    assert state["peak"] == 2 and state["lights"]["living"] == 0
    assert state["offpeak"] == .16 and state["hvac"] == "heat"
    assert np.isfinite(simulate(state).totals["cost"])


def test_csv_reconciles_to_displayed_totals():
    from app import export_csv
    state = default_state()
    state["dr"] = True
    day, reference, event = evaluate_state(state)
    rows = list(csv.DictReader(io.StringIO(export_csv(state))))
    assert len(rows) == 96
    assert sum(float(r["net_cost_eur"]) for r in rows) == pytest.approx(day.totals["cost"], abs=1e-6)
    assert sum(float(r["reference_net_cost_eur"]) for r in rows) == pytest.approx(reference.totals["cost"], abs=1e-6)
    assert sum(float(r["flex_reward_eur"]) for r in rows) == pytest.approx(event["reward"], abs=1e-6)
    assert sum(float(r["home_kw"]) * DT for r in rows) == pytest.approx(day.totals["load"], abs=1e-6)
    assert all(r["mode"] == "SIMULATED" for r in rows)

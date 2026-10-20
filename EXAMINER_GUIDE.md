# Verdant — examiner demonstration

This project is a **Python Smart Home Energy Management demonstrator**. All data and controls are simulated; calculations and assumptions are inspectable. No electricity-provider, meter or physical-device connection is claimed.

## Five-minute walkthrough

1. **Overview:** observe the actual Irish analog/digital clock and model-time label. Inspect **Roof on** for the complete envelope and 13 rooftop PV modules. Identify the driveway EV, charging cable, wall-mounted residential battery and heat pump. Drag to orbit, scroll/right-drag to zoom, try **+ / −**, camera presets and **Reset view**. Switch to **Inside** or **X-ray** to inspect the furnished rooms.
2. **Dynamic demonstration:** select **Play day ×300**. Watch power, solar, grid flows, battery fill, moving energy particles and modelled indoor temperatures evolve. A model day takes about 4 minutes 48 seconds. The actual header clock stays on Irish local time. Select **Inspect time** and move the slider to 18:00 for evening conditions, or restore **Irish time**.
3. **Devices & lighting:** click a gold bulb in the interior. It turns grey, its floor light disappears, and the matching dimmer/room switch and demand update. Click again to restore its previous brightness. Click the EV or another equipment symbol and inspect its immediate power/status change; the adjacent equipment key uses matching distinct symbols. **Restore automatic schedules** clears live overrides. Daily schedule switches and tariff optimization separately change full-day projections. **Eco** sets lights to 35% and heating to 19°C.
4. **Heating & cooling:** change the target, compare daily electrical demand, and try Off. The climate chart displays daily target/outdoor assumptions. Live indoor temperatures in Overview/Devices evolve through a simplified room RC heat balance, not connected sensors. Playback makes slow thermal changes easier to see.
5. **Demand response:** participate in the fictional 17:00–19:00 event. Compare import with an otherwise identical schedule-based scenario without DR. Inspect event reduction and the illustrative reward.
6. **Energy analytics:** compare seven or thirty independent synthetic days with the reference, inspect demand/cost/carbon and the ledger, then **Export CSV**. Sum interval costs to reconcile to the daily projections. Live overrides and session counters are excluded from this CSV.
7. **System & assumptions:** inspect rates, emission factor, asset sizes, thermal assumptions, baseline and battery boundary. Disable solar or storage to test their effects.

## Numerical checks

- `PV + battery_discharge + grid_import = home_demand + battery_charge + grid_export` for every interval, in kW.
- Daily intervals: `energy_kWh = power_kW × 0.25 hours`. Live session energy uses elapsed model hours.
- Import and export cannot occur simultaneously; neither can battery charge and discharge.
- Battery state remains between 2 and 10 kWh while enabled. AC charge/discharge power is limited to 2.5 kW, with conversion losses on each side.
- `daily_cost = interval import charges − interval export credits + daily standing charge`.
- `operational_carbon = imported_kWh × assumed_grid_factor`.
- `financial_saving = reference_cost − scenario_cost + illustrative_flex_reward`.
- Reference: 22°C heating, 80% lighting, default devices/windows, matching solar setting, no battery/optimization/DR.

## Limits to acknowledge during the assessment

The geometry and RC thermal dynamics are illustrative, not a surveyed or physically validated house. Live manual On holds an appliance's declared rated electrical power; detailed appliance cycles and EV traction-battery state are not modelled. The battery starts each independent daily projection with 5 kWh already stored and no acquisition cost/emissions. Daily savings can include a drawdown of that energy. Live battery state initializes from the projection at the selected time and then integrates. Multi-day graphs replay independent scenarios. Time jumps/inactivity reset the live session. Tariffs/carbon factors are assumptions, and controls are not connected to hardware.

## Shareable link

Send the actual HTTPS URL from the deployed Render Web Service after verifying it in an incognito browser. `127.0.0.1`/`localhost` are local preview addresses and must not be submitted as a public examiner link. See `README.md` for the full deployment procedure.

# Smart — examiner demonstration

This project is a **Python Smart Home Energy Management demonstrator**. All data and controls are simulated; calculations and assumptions are inspectable. No electricity-provider, meter or physical-device connection is claimed.

## Five-minute walkthrough

1. **Overview:** observe the actual Irish analog/digital clock and model-time label. Inspect **Roof on** for the complete envelope and 13 rooftop PV modules. Identify the driveway EV, charging cable, wall-mounted residential battery and heat pump. Drag to orbit, scroll/right-drag to zoom, try **+ / −**, camera presets and **Reset view**. Switch to **Inside** or **X-ray** to inspect the furnished rooms.
2. **Dynamic demonstration:** select **Play day ×300**. Watch power, solar, grid flows, battery fill, moving energy particles and modelled indoor temperatures evolve. A model day takes about 4 minutes 48 seconds. The actual header clock stays on Irish local time. In Devices, select **Day preview** and **Night preview**: the sun changes to a moon/stars, the building darkens and streetlights switch automatically. Sunrise/sunset are approximate for the Dublin demo location and current date; the moon is a night symbol. Restore **Irish time** to follow the real local time.
3. **Devices & lighting:** click a gold bulb in the interior. Its whole-room glow disappears and its tile becomes dark **OFF**, shows **0 W**, and empties its brightness bar. Click again to restore the previous brightness and gold **ON** state. The total number of lit rooms and lighting watts update together. Click an equipment symbol for immediate live operation; the adjacent key uses matching symbols. **Restore automatic schedules** clears live overrides. Daily schedules and tariff optimization separately change full-day projections. **Eco** sets lights to 35% and heating to 19°C.
4. **Heating & cooling:** change the target, compare daily electrical demand, and try Off. The climate chart displays daily target/outdoor assumptions. Live indoor temperatures in Overview/Devices evolve through a simplified room RC heat balance, not connected sensors. Playback makes slow thermal changes easier to see.
5. **Demand response:** inspect the pylon → local transformer → meter → home network schematic. Select **Preview event · 18:00** and enable participation. Observe the event countdown and matched meter-import readings. Adjust load shifting, lighting reduction, thermostat relief and reward rate. Compare event kWh, the signed contribution chart and each appliance's before/after operating window. Check peak import and full-day bill benefit; negative bill benefits remain visible. The network uses daily projections, not live manual overrides.
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
- DR reward is `max(0, matched event import reduction) × configured €/kWh` (default 0.35). Signed appliance/lighting/HVAC contributions plus storage interaction sum to the unclipped import change.
- Reference: 22°C heating, 80% lighting, default devices/windows, matching solar setting, no battery/optimization/DR.

## Limits to acknowledge during the assessment

The geometry, network and RC dynamics are illustrative, not a surveyed house, wiring design or physically validated building. Sun events use approximate solar equations; no weather measurements or astronomical moon phase are supplied. Public streetlights are outside household energy/cost accounting. Live manual On holds rated electrical power; detailed appliance cycles and EV traction-battery state are not modelled. Each independent daily projection starts with 5 kWh already stored and no acquisition cost/emissions. Daily savings can include that energy drawdown. Live battery state initializes from the projection at the selected time, then integrates. Multi-day graphs replay independent scenarios. Time jumps/inactivity reset the live session. Tariffs/carbon factors and DR rates are assumptions; controls are not connected to hardware.

## Shareable link

Open or share [https://behnamproject-smarthome.onrender.com/](https://behnamproject-smarthome.onrender.com/). The public deployment was verified on **21 October 2026**. Visitors do not need a Render/GitHub login or Python installation; the developer's computer does not need to stay running. On the Free plan, an inactive service can take about a minute to wake, followed by the initial 3D asset download. Open the dashboard ahead of the assessment and use a modern WebGL-capable browser. A paid compute plan is needed for always-running hosting. See `README.md` for deployment and `docs/VERIFICATION.md` for the validation scope.

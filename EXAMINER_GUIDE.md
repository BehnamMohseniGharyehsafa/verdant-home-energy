# Verdant — examiner demonstration

This project is a **Python Smart Home Energy Management demonstrator**. All data and controls are simulated; calculations and assumptions are inspectable. No electricity-provider, meter or physical-device connection is claimed.

## Five-minute walkthrough

1. **Overview:** rotate and zoom the furnished 3D home. Click a labelled room or select it in the dropdown. Switch between Rooms, Energy and Lighting. Move the time explorer to 18:00 and inspect power, solar and tariff changes.
2. **Devices & lighting:** disable a daily appliance window and observe the overview and analytics change. Select **Eco** to set all lights to 35% and heating to 19°C. Enable cheapest-tariff scheduling and inspect its operating windows. It optimizes cycle tariff cost, not the full solar/battery system.
3. **Heating & cooling:** change the target, compare electrical demand, and try Off. The temperature chart displays a target and assumed outdoor conditions, not measured indoor temperatures.
4. **Demand response:** participate in the fictional 17:00–19:00 event. Compare import with an otherwise identical scenario without DR. Inspect event reduction and the illustrative reward.
5. **Energy analytics:** compare seven or thirty independent synthetic days with the reference, inspect demand/cost/carbon and the ledger, then **Export CSV**. Sum the interval cost fields to reconcile to the daily totals.
6. **System & assumptions:** inspect rates, emission factor, asset sizes, loss model, baseline and battery boundary. Disable solar or storage to test their effects.

## Numerical checks

- `PV + battery_discharge + grid_import = home_demand + battery_charge + grid_export` for every interval, in kW.
- `energy_kWh = power_kW × 0.25 hours`.
- Import and export cannot occur simultaneously; neither can battery charge and discharge.
- Battery state remains between 2 and 10 kWh while enabled. AC charge/discharge power is limited to 2.5 kW, with conversion losses on each side.
- `daily_cost = interval import charges − interval export credits + daily standing charge`.
- `operational_carbon = imported_kWh × assumed_grid_factor`.
- `financial_saving = reference_cost − scenario_cost + illustrative_flex_reward`.
- Reference: 22°C heating, 80% lighting, default devices/windows, matching solar setting, no battery/optimization/DR.

## Limits to acknowledge during the assessment

The model is not a physical building simulator, real-time tariff service or validated forecast. The battery starts each independent day with 5 kWh already stored and no associated acquisition cost/emissions. Daily savings can include a drawdown of that stored energy. Multi-day graphs replay independent scenarios rather than carrying storage state across days. Tariffs/carbon factors are assumptions, and controls are not connected to hardware.

## Shareable link

Send the actual HTTPS URL from the deployed Render Web Service after verifying it in an incognito browser. `127.0.0.1`/`localhost` are local preview addresses and must not be submitted as a public examiner link. See `README.md` for the full deployment procedure.

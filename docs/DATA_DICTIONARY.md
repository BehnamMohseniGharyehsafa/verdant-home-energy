# CSV data dictionary

The **Export CSV** button downloads 96 rows for the selected scenario's complete model day. The time explorer does not restrict the export to a single interval. Numbers are rounded to eight decimal places at serialization; small differences from summing displayed two-decimal values are expected.

| Column | Unit / meaning |
|---|---|
| `model_date` | ISO date of the fixed scenario day |
| `time` | Interval start, `HH:MM`; final interval starts at 23:45 |
| `interval_hours` | Hours per interval, always 0.25 |
| `home_kw` | Total end-use electrical demand, kW |
| `solar_kw` | Available PV generation, kW |
| `battery_charge_kw` | AC-side charging input, kW |
| `battery_discharge_kw` | AC-side battery output serving demand, kW |
| `battery_soc_start_kwh` | Stored energy at interval start, kWh |
| `battery_soc_end_kwh` | Stored energy at interval end, kWh |
| `grid_import_kw` | Non-negative import from the grid, kW |
| `grid_export_kw` | Non-negative export to the grid, kW |
| `import_eur_per_kwh` | Applicable illustrative import price, €/kWh |
| `export_eur_per_kwh` | Assumed export credit, €/kWh |
| `standing_charge_eur` | Daily standing charge allocated once to the first row; zero in subsequent rows |
| `net_cost_eur` | Interval import cost minus export credit plus any allocated standing charge, € |
| `carbon_kg_co2e` | Interval grid imports × 0.25 h × assumed carbon factor, kg CO₂e |
| `reference_home_kw` | Declared reference end-use demand, kW |
| `reference_import_kw` | Reference grid import, kW |
| `reference_export_kw` | Reference grid export, kW |
| `reference_net_cost_eur` | Reference interval net cost including any allocated standing charge, € |
| `flex_reward_eur` | Whole-day illustrative event reward allocated once to the first row; zero otherwise |
| `grid_carbon_kg_per_kwh` | Assumed constant grid-import carbon factor, kg CO₂e/kWh |
| `mode` | Always `SIMULATED` |

The standing charge and reward appear in the first row as a bookkeeping convention. **They do not represent a charge or an event occurring at midnight.** The flex event is 17:00–19:00.

## Reconciliation examples

```python
import csv

with open("verdant-simulated-2026-10-20.csv", newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

energy_kwh = sum(float(r["home_kw"]) * float(r["interval_hours"]) for r in rows)
cost_eur = sum(float(r["net_cost_eur"]) for r in rows)
reference_eur = sum(float(r["reference_net_cost_eur"]) for r in rows)
reward_eur = sum(float(r["flex_reward_eur"]) for r in rows)
saving_eur = reference_eur - cost_eur + reward_eur
carbon_kg = sum(float(r["carbon_kg_co2e"]) for r in rows)
```

The overview's projected electricity cost is `cost_eur`, **excluding** reward. The analytics financial-savings measure includes the separately identified reward. Battery start/end fields expose any net drawdown of initially stored energy.

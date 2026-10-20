# Verdant — Smart Home Energy Management

A complete, Python-authored Dash application for an examiner-facing smart-home energy demonstration. The interface, Plotly charts, furnished 3D geometry, callbacks, scheduling and energy calculations are authored in Python. Local CSS supplies the visual theme; there is no handwritten application JavaScript or separate frontend build.

[Source repository](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy) · [Deploy to Render](https://render.com/deploy?repo=https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy)

**Data and controls are simulated.** The app does not claim to be connected to meters, appliances, electricity markets, a real demand-response program or an AI service. It works without API keys or personal home data.

## Run locally

Python **3.13.7** is the pinned deployment runtime. Python 3.11–3.13 should support the source, but only the pinned runtime has been checked here. A WebGL-capable modern desktop browser is needed for the 3D home.

From this project folder, on Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8050/**. Keep the terminal running. This local URL cannot be used by your examiner on another computer. If the port is occupied, set `$env:PORT = '8051'` before starting and use that port in the browser.

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## Deploy to Render and obtain the examiner link

The included `render.yaml` provisions a **Python Web Service**, with Gunicorn and a `/healthz` health check. No database, paid API, static-site build or Node.js runtime is required. These instructions follow the official [Render Flask deployment guide](https://render.com/docs/deploy-flask), [Blueprint reference](https://render.com/docs/blueprint-spec) and [Python-version settings](https://render.com/docs/python-version).

1. Use [this GitHub repository](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy). The project source has `app.py`, `requirements.txt`, `render.yaml` and `assets/` at its root. Alternatively, upload the prepared release ZIP's extracted contents to your own repository. Do **not** upload `.venv/`, `.git/`, caches, `.env` or the ZIP itself as the app source.
2. Sign in at [Render](https://dashboard.render.com/). Select **New → Blueprint**, connect your GitHub account and select that repository. Render reads `render.yaml`.
3. Review the service and the **Free** instance setting, then deploy. If `verdant-home-energy` is unavailable, choose a unique service name.
4. Wait for the deployment to report **Live**. Open the HTTPS URL Render actually assigns. Do not invent the hostname from the service name.
5. Open that URL in an incognito window. Check that the overview loads, the 3D home renders, controls update the graphs, and Export CSV downloads. The examiner should not need your Render account.
6. Send the verified **HTTPS Render URL** to your examiner. This URL does not depend on your local terminal remaining open.

If using **New → Web Service** instead of a Blueprint, select the repository and enter:

| Setting | Value |
|---|---|
| Runtime | Python |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:server --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120 --access-logfile -` |
| Health check | `/healthz` |
| `PYTHON_VERSION` | `3.13.7` |
| `DEMO_DATE` | `2026-10-20` |

Render's free web services can spin down after 15 minutes of inactivity, and waking can take about a minute. Free-tier limits can change; check [Render's current free-service documentation](https://render.com/docs/free). Open the app ahead of an assessment. Choose a paid instance only if you decide an always-running service is needed.

**Publication status:** the source repository and deployment configuration are prepared. A permanent public dashboard URL is only confirmed once the app is deployed in your Render account. The GitHub project link is a source-code link; the local preview is not a public deployment.

## What is included

| View | Features |
|---|---|
| Overview | Daily demand/cost/carbon indicators, interactive furnished 3D home, selectable rooms, energy and lighting layers, quarter-hour time explorer, power-flow diagram, demand and solar profile, editable-tariff chart, scenario insights |
| Devices & lighting | Six daily appliance schedules, EV charging, six room dimmers, Home/Eco/Away scenes, contiguous-cycle tariff scheduler and timeline |
| Heating & cooling | Thermostat, heating/cooling/off, target/outdoor profiles, electrical demand and model assumptions |
| Energy analytics | 7/30-day synthetic replays, reference comparisons for cost/demand/carbon, consumption breakdown and full daily ledger |
| Demand response | Event participation simulator, load shifting, event dimming, thermostat relief, matched grid-import comparison and illustrative reward |
| System & assumptions | Solar/battery availability, rates, export credit, standing charge, grid carbon factor, formulas, boundaries and examiner walkthrough |

CSV export includes 96 intervals with scenario and reference powers, battery state, prices, interval costs, standing charge, carbon and flex reward. It reconciles with the daily indicators.

## Model specification

- **Time:** a fixed 24-hour model day, 96 × 15-minute intervals; not a clock or DST-aware meter series. Default date is 20 October 2026, configurable with `DEMO_DATE`. Moving the time slider selects an interval. Controls re-run the entire day and are not logged historical commands.
- **Building:** 128 m² including garage; six rooms. Geometry is illustrative, not surveyed. Whole-home HVAC and always-on power are allocated to rooms in proportion to area; scheduled appliances and room lighting are assigned directly. Room allocations sum to total demand.
- **Lighting:** 296 W total installed power at 100%; power varies linearly with brightness. From 08:00 to 17:00, daylight reduces selected power to 30%. This is an energy assumption, not a lux/illuminance model.
- **Always-on:** 110 W combined fridge/router/standby load. It cannot be remotely disabled in this demonstration.
- **HVAC:** quasi-steady heat-loss coefficient 0.18 kW/°C; heating COP 3.5 and cooling COP 3.2; simple passive gains. Outdoor temperature is synthetic autumn weather. No thermal capacitance, measured indoor temperature, occupancy dynamics or room thermostat loop is simulated. Cooling can legitimately be zero on a cool day.
- **Appliances:** one fixed-profile daily cycle/window each when enabled. Washer 1.00 kWh; dishwasher 0.90 kWh; water heater 2.00 kWh; EV 10.80 kWh; oven 1.45 kWh; office 1.12 kWh. EV charging is disabled initially. Toggling a device enables/disables its daily window; it is not an instantaneous physical switch.
- **Scheduling:** exhaustively evaluates allowed contiguous starts for each flexible cycle at the import tariff. Cycles complete within the same day, with earliest-start tie breaking. All-day unattended operation is assumed. Tariff-only optimization can increase whole-home net cost because PV/battery effects are not its objective; the interface explicitly states this limitation.
- **PV:** 5.2 kWp with deterministic synthetic daylight and cloud variation; no weather API or site-specific yield model. Default-day output is about 18 kWh, an illustrative favorable autumn day, not a generation forecast. Turning solar off also disables it in the matched reference.
- **Battery:** 10 kWh, 2.5 kW AC charge/discharge limit, 20% reserve, 90% round-trip efficiency. Each conversion uses `sqrt(0.9)` efficiency. Surplus PV charges the battery; deficits discharge it above reserve. Charging from the grid is not modeled.
- **Important battery boundary:** each independent day starts with 5 kWh already stored, assigned no acquisition cost or carbon. Ending energy can differ. The fixed reference has battery disabled. Daily savings therefore include the benefit of initially stored energy and are not an annual performance claim. The app displays ending charge and explains this boundary. Multi-day replays reset charge each day.
- **Tariff:** illustrative €0.16/kWh 00:00–07:00; €0.42/kWh 17:00–19:00; €0.28/kWh otherwise; export credit €0.12/kWh and standing charge €0.65/day. All are editable. No named supplier, tax treatment, network fee or current Irish tariff is claimed.
- **Cost:** `sum((import_kW × import_rate − export_kW × export_rate) × 0.25 h) + standing_charge`. Negative values indicate a net credit under the assumptions. Electricity-cost charts exclude flex reward; the separately labelled financial-savings metric includes it.
- **Carbon:** imported kWh × editable default **0.23 kg CO₂e/kWh**. This is an assumed constant, not a verified current grid factor. Lifecycle impacts, fuel use and exported-electricity offsets are excluded.
- **Reference:** 22°C heating, 80% room brightness, default enabled appliances and operating windows, solar matching the scenario, battery disabled, scheduling and DR disabled. Same weather, prices, standing charge and emission factor. Adding EV demand can produce negative savings; negative savings are retained.
- **DR:** fictional 17:00–19:00 event. Flexible cycles avoid it, lighting power halves, heating target reduces 1°C/cooling increases 1°C. Reduction is `max(0, sum(import_without_DR − import_with_DR) × 0.25 h)` over the event. Counterfactual preserves all other scenario settings. Illustrative reward = reduction × €0.35/kWh. No enrollment, eligibility claim or payment is performed.
- **History:** synthetic daily variation replayed under current settings, not measured history or a forecast. No artificial percentage achievements or tree-equivalent sustainability claims are shown.

## Test

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Checks include interval conservation, battery losses/limits, room reconciliation, a hand-calculated cost/carbon case, tariff boundaries, cycle-preserving optimal tariff starts, DR settlement, invalid input, CSV totals, all page renderers, HTTP routes and a real Dash callback POST. GitHub Actions also starts the actual Gunicorn production entry point on Linux and checks its HTTP health and layout routes; that platform-specific check is skipped on Windows.

## Architecture and operational notes

```text
app.py             Dash app, callbacks, health check and CSV export
energy.py          Deterministic energy model and reference calculations
house.py           Furnished Plotly Mesh3d home and room overlays
charts.py          Python/Plotly analytics and flows
ui.py              Python-authored layouts, components and vector icons
assets/style.css   Responsive dark theme, accessibility and controls
render.yaml        Render Web Service Blueprint
Dockerfile         Optional container deployment
tests/             Accounting and HTTP/callback tests
```

Scenario controls live in browser memory and reset on refresh; visitors do not share a mutable global home. Server-side cached results are deterministic and bounded. There is no database, persistent household data, authentication, API key or external API dependency. The production start command uses one Gunicorn worker with four threads to suit a small service; do not use Flask's development server for public deployment. Dash/Plotly ship their own browser runtime as part of the Python framework.

The 3D model and charts have no added watermark. Plotly's modebar and logo are explicitly disabled, and visible framework credits are omitted from the interface. The Verdant name is the application's own identity. Third-party license notices remain in their distributed dependencies.

To connect real equipment later, implement authenticated server-side adapters for an actual platform (for example Home Assistant/MQTT), validate device capabilities, store verified meter/tariff data, and replace the simulation with measured series. Those integrations, access control, physical-device safety rules and hardware validation are a separate implementation task. Do not expose a real-home controller publicly using this demonstration's anonymous visitor model.

Official framework reference: [Dash installation](https://dash.plotly.com/installation), [Dash callbacks](https://dash.plotly.com/basic-callbacks), [Plotly Python 3D meshes](https://plotly.com/python/3d-mesh/).

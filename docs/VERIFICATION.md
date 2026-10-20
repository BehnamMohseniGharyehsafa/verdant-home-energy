# Verification record

Verified on **20 October 2026**. These checks validate implementation and internal accounting, not the physical accuracy of a real house or a future hosting account's service availability.

## Automated checks

- Isolated local environment: Python 3.13.7, Dash 2.18.2, bundled React 16.14.0, dash-vtk 0.0.9, Plotly 6.3.0, NumPy 2.3.3 and tzdata 2026.5. `pip check`: **no broken requirements**.
- Windows: **39 passed, 1 skipped**. The skipped check starts Gunicorn and is specific to Linux.
- Ubuntu/GitHub Actions: **successful** for the updated implementation, commit `633d96f5eb26c9e998aef556f44b267938066dee`. [Verified production-check run](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39434361354). The workflow installs the same requirements and starts the actual Gunicorn production entry point, including `/healthz` and Dash layout routes.
- Daily and live power conservation, battery losses/capacity/power limits, room allocation, tariff boundaries, bill/carbon arithmetic, cycle-preserving scheduling, matched DR reward, invalid parameters and CSV reconciliation all pass.
- New checks cover Irish GMT/IST daylight-saving boundaries, clock/playback/manual modes, evolving room thermal state, live EV On/Off power, live overrides excluded from daily projections, inactive-session resets, valid mesh normals/colors/indices, distinct control IDs, stable actor order across envelope modes, small scene patches and zoom transforms.
- Actual Dash HTTP POSTs verify a 3D bulb switches off and restores its remembered dim level on the next click, both consumed pick states clear, EV picks apply live overrides, and architectural surfaces cannot trigger devices.

## Browser checks

- Detailed complete envelope and slate roof render with 13 rooftop PV modules, visible EV/charger/cable, residential battery and heat pump. Furnished interior and transparent X-ray modes render correctly.
- Explicit Zoom in/out and Reset view work, and zoom remains in place through live ticks. Native VTK orbit/pan/dolly controls are available.
- A **direct click on the 3D living-room bulb** switches it off, updates its dimmer and removes its light pool; clicking the same location again restores 65%. A **direct 3D EV-symbol click** switches charging off. Adjacent room/equipment buttons also update the same state.
- The actual Irish clock advances independently of model playback. Accelerated playback changes live demand, solar, grid flow, battery charge and indoor temperature; returning to Irish time restores local-time conditions.
- Home/Eco scenes update room dimmers and thermostat targets.
- Enabling the EV schedule changes modeled demand; tariff scheduling updates flexible operating windows to off-peak starts.
- Thermostat keyboard control updates the target.
- DR participation updates the event comparison and illustrative reward; a scenario with already-shifted loads can correctly yield no additional event reduction.
- 30-day analytics produces 30 daily ledger rows.
- CSV downloads successfully and its totals reconcile in automated tests.
- Desktop and phone layouts inspected; no horizontal page overflow after responsive charts resize. Collapsed navigation retains accessible labels.
- No browser console errors were observed in the tested interactions.
- Framework credits omitted and Plotly modebar/logo disabled. Simulation disclosures intentionally remain visible.

## Visual evidence

- [Desktop overview](images/overview.jpg)
- [Interactive furnished interior](images/interior.jpg)
- [Demand-response simulator](images/demand-response.jpg)
- [Energy analytics](images/analytics.jpg)
- [Phone overview](images/mobile.jpg)

## Publication boundary

The source project is published to GitHub. Render's account session was signed out during preparation. **A public Render dashboard deployment is not yet verified**, and the local preview must not be presented as an examiner-accessible internet URL. Use the repository's Deploy to Render link after signing in, then verify the actual assigned HTTPS URL in a separate browser session.

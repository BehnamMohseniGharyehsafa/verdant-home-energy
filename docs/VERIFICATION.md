# Verification record

Verified on **20 October 2026**. These checks validate implementation and internal accounting, not the physical accuracy of a real house or a future hosting account's service availability.

## Automated checks

- Isolated local environment: Python 3.13.7; pinned top-level Dash, Plotly and NumPy dependencies. `pip check`: **no broken requirements**.
- Windows: **17 passed, 1 skipped**. The skipped check starts Gunicorn and is specific to Linux.
- Ubuntu/GitHub Actions: **successful**, including the actual Gunicorn production entry point and its `/healthz` and Dash layout routes. [Verified code run](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39413674006) for commit `d22528b4688e618a3ac4cacba2181a2d3329195b`.
- Interval conservation, battery losses/capacity/power limits, tariff boundaries, room allocation reconciliation, a hand-calculated bill/carbon case, energy-preserving tariff scheduling, matched DR reward, controls, invalid parameters, CSV reconciliation, callback registration and HTTP callback execution all pass.

## Browser checks

- Furnished 3D home and room dropdown render; house camera can be explored.
- Home/Eco scenes update room dimmers and thermostat targets.
- Enabling the EV schedule changes modeled demand; tariff scheduling updates flexible operating windows to off-peak starts.
- Thermostat keyboard control updates the target.
- DR participation updates the event comparison and illustrative reward; a scenario with already-shifted loads can correctly yield no additional event reduction.
- 30-day analytics produces 30 daily ledger rows.
- CSV downloads successfully and its totals reconcile in automated tests.
- Desktop and 390-pixel phone layouts inspected; no horizontal page overflow after responsive charts resize. Collapsed navigation retains accessible labels.
- No browser console errors were observed in the tested interactions.
- Framework credits omitted and Plotly modebar/logo disabled. Simulation disclosures intentionally remain visible.

## Visual evidence

- [Desktop overview](images/overview.jpg)
- [Demand-response simulator](images/demand-response.jpg)
- [Energy analytics](images/analytics.jpg)
- [Phone overview](images/mobile.jpg)

## Publication boundary

The source project is published to GitHub. Render's account session was signed out during preparation. **A public Render dashboard deployment is not yet verified**, and the local preview must not be presented as an examiner-accessible internet URL. Use the repository's Deploy to Render link after signing in, then verify the actual assigned HTTPS URL in a separate browser session.

# Verification record

Verified on **20 October 2026**. These checks validate implementation and internal accounting, not the physical accuracy of a real house or a future hosting account's service availability.

## Automated checks

- Isolated local environment: Python 3.13.7, Dash 2.18.2, bundled React 16.14.0, dash-vtk 0.0.9, Plotly 6.3.0, NumPy 2.3.3 and tzdata 2026.5. `pip check`: **no broken requirements**.
- Windows: **47 passed, 1 skipped**. The skipped check starts Gunicorn and is specific to Linux.
- Linux production checks: **successful** for commit `74515dd5a9c576ba2c83ffb03a97196a751d6132`. [Verified run](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39447732103). The workflow installs the same requirements and starts the actual Gunicorn production entry point, including `/healthz` and Dash layout routes.
- Daily and live power conservation, battery losses/capacity/power limits, room allocation, tariff boundaries, bill/carbon arithmetic, cycle-preserving scheduling, matched DR reward, invalid parameters and CSV reconciliation all pass.
- New checks cover Irish GMT/IST daylight-saving boundaries, clock/playback/manual modes, evolving room thermal state, live EV On/Off power, live overrides excluded from daily projections, inactive-session resets, valid mesh normals/colors/indices, distinct control IDs, stable actor order across envelope modes, small scene patches and zoom transforms.
- Actual Dash HTTP POSTs verify a 3D bulb switches off and restores its remembered dim level on the next click, both consumed pick states clear, EV picks apply live overrides, and architectural surfaces cannot trigger devices.
- New checks cover Dublin sunrise/sunset sanity bounds, the Irish DST clock change, seasonal day/night behavior, public lights outside the household meter, zero PV after sunset, configurable DR cycle-energy preservation, contribution reconciliation, zero-strategy/opt-out rewards, live versus network model boundaries and actual Dash strategy inputs reaching the model/CSV.
- Sunrise/sunset displays remain consistent before and after the overnight clock transition on both the spring and autumn DST-change dates.

## Browser checks

- Detailed complete envelope and slate roof render with 13 rooftop PV modules, visible EV/charger/cable, residential battery and heat pump. Furnished interior and transparent X-ray modes render correctly.
- Explicit Zoom in/out and Reset view work, and zoom remains in place through live ticks. Native VTK orbit/pan/dolly controls are available.
- A **direct click on the 3D living-room bulb** switches it off, updates its dimmer and removes its light pool; clicking the same location again restores 65%. A **direct 3D EV-symbol click** switches charging off. Adjacent room/equipment buttons also update the same state.
- The actual Irish clock advances independently of model playback. Accelerated playback changes live demand, solar, grid flow, battery charge and indoor temperature; returning to Irish time restores local-time conditions.
- Smart branding, sun/moon/stars, daytime/nighttime shading, refined trees/EV and automatic streetlights render. Night preview switches the streetlights on; Day preview and Irish time restore the appropriate solar-clock state.
- Room switches show gold ON or dark OFF tiles, brightness bars and lighting-only watts. Switching the living room off at night changes six lit rooms to five, removes 54.6 W of lighting and removes that room's floor glow.
- The demand-response pylon/transformer/meter/house scene renders. Participation and event preview update status/countdown; changing thermostat relief and reward updates the strategy text and reward calculation. The signed contribution chart and appliance-plan table render.
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
- [Night lighting and automatic streetlights](images/night.jpg)
- [Demand-response simulator](images/demand-response.jpg)
- [Demand-response contribution analytics](images/demand-response-analytics.jpg)
- [Energy analytics](images/analytics.jpg)
- [Phone lighting controls](images/mobile.jpg)

## Publication boundary

The source project is published to GitHub. Render's account session was signed out during preparation. **A public Render dashboard deployment is not yet verified**, and the local preview must not be presented as an examiner-accessible internet URL. Use the repository's Deploy to Render link after signing in, then verify the actual assigned HTTPS URL in a separate browser session.

On **21 October 2026**, the Blueprint was updated to request `behnamproject-smarthome` on branch `main` in Frankfurt, using the Free compute plan. The requested `/healthz` address returned HTTP 404 and Render required account sign-in; this is a deployment target, not a confirmed live link. The local full suite passed **47 tests, with 1 Linux-only Gunicorn check skipped on Windows**. GitHub's Linux checks for the preceding application commit `98f50c9989a5240764ebfc7b5483aa3a6f5b7232` also passed ([run](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39632004707)).

## Developer header update · 21 October 2026

The shared top header now displays the supplied developer name, qualification and email, centered above every dashboard view. The email is a `mailto:` link. Desktop (1440 px), laptop breakpoint (1281 px) and phone (390 px) layouts were inspected; the phone header puts the developer details above the navigation/clock row. The existing HTTP/layout smoke check passed. [Desktop evidence](images/developer-header.jpg) · [Phone evidence](images/developer-header-mobile.jpg).

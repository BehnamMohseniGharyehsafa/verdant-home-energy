# Verification record

Verified on **20–21 October 2026**, with public deployment checks on **21 October**. These checks validate implementation and internal accounting, not the physical accuracy of a real house or a guarantee of future hosting availability.

## Automated checks

- Isolated local environment: Python 3.13.7, Dash 2.18.2, bundled React 16.14.0, dash-vtk 0.0.9, Plotly 6.3.0, NumPy 2.3.3 and tzdata 2026.5. `pip check`: **no broken requirements**.
- Windows: **48 passed, 1 skipped** after the deployment reliability changes. The skipped check starts Gunicorn and is specific to Linux.
- Linux production checks: **successful** for deployed application commit `c7c4ea346cdefbb50ca87c9178addd5bbdc5ab8a`. [Verified run](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39636564003). The workflow installs the same requirements and starts the actual Gunicorn production entry point, including `/healthz` and Dash layout routes.
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

## Public deployment verified · 21 October 2026

The public simulation is [https://behnamproject-smarthome.onrender.com/](https://behnamproject-smarthome.onrender.com/). Render service `srv-dbcebdvf3r2c739pjh2g` runs the Python application on the **Free** compute plan in **Frankfurt**. Application commit `c7c4ea346cdefbb50ca87c9178addd5bbdc5ab8a` was deployed successfully. Verification used a separate browser session without a Render login and unauthenticated HTTP requests.

- `/`, `/healthz`, `/_dash-layout`, `/_dash-dependencies` and the experience stylesheet returned HTTP 200. The health response identifies the Smart simulation.
- The opening HTML is about **4.8 KB**, reduced from an unnecessary 11 MB validation copy. Callback validation remains enabled. An HTTP regression check ensures repeat navigation sends small scene patches instead of full meshes.
- The Irish clock and model readings advance; the furnished house and grid scene render. At the 18:00 DR preview, enabling participation changes the matched import comparison and reward (in the checked scenario, 1.74 kW to 0.00 kW at the selected time and 0.85 kWh event reduction).
- Public light picks switch off and restore the remembered 65% level; EV picks apply an On override. The browser displayed five lit rooms after one room was switched off and six lit rooms in a fresh session. Night preview displays the moon and automatic street lights; EV control displays 3600 W when manually on.
- The public CSV callback returns **96 data rows** with the expected energy, tariff, cost, carbon and DR columns. A browser CSV download was also checked during deployment.
- Three simultaneous opening requests returned HTTP 200 in approximately 0.9–1.02 seconds in the checked run. Six health requests during the response exercise all succeeded (maximum observed latency 2.5 seconds). This is a small smoke check, not a capacity benchmark or uptime guarantee.
- An opaque browser-console entry labelled `Object` appeared during startup. No matching Render application `ERROR` records were found for the inspected hour; the tested controls and views completed successfully. This record does not claim a completely silent browser console.

Render Free can sleep after 15 minutes without traffic, takes about a minute to wake and can restart. Initial 3D assets also require download/render time. An always-running service requires a paid compute plan. Visitors need a modern WebGL-capable browser. No uptime guarantee or paid upgrade was purchased.

[Deployed overview](images/render-live-overview.png) · [Deployed night lighting](images/render-live-night.png).

## Developer header update · 21 October 2026

The shared top header now displays the supplied developer name, qualification and email, centered above every dashboard view. The email is a `mailto:` link. Desktop (1440 px), laptop breakpoint (1281 px) and phone (390 px) layouts were inspected; the phone header puts the developer details above the navigation/clock row. The existing HTTP/layout smoke check passed. [Desktop evidence](images/developer-header.jpg) · [Phone evidence](images/developer-header-mobile.jpg).

## Security hardening · 21 October 2026

Application commit `5b4ff52febab202b1561dc9d81bb7a67dab39114` was deployed to the same public URL as release `2026.10.21-security.1`, using Render deployment `dep-dbcfbt8m7kps73fj2dag`. A superseded deployment was cancelled before finishing after the callback validator's browser-format compatibility issue was identified and corrected. The earlier public release stayed available during that correction.

- Patched framework: Dash **3.4.0**, React **16.14.0**, Flask **3.1.3**, Werkzeug **3.1.9**; dash-vtk remains **0.0.9**. Pytest is **9.0.3**. `pip check` reports no broken requirements. A fresh `pip-audit` resolution of production **and development** requirements covered **39 packages** and reported **no known vulnerabilities**. This does not audit bundled JavaScript or certify absence of unknown vulnerabilities.
- Windows: **62 passed, 1 skipped**; the skip is the Linux-only Gunicorn test. [Linux CI and dependency audit passed](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/actions/runs/39643521157). The new security tests cover request size/depth, invalid callback targets/types, unexpected output IDs, forged live-state structure, cross-site origins, invalid hosts, secret/source paths, rate-limit responses, bounded concurrent work and actual browser-format grouped lighting inputs.
- Public smoke check: `/healthz`, root HTML, callback metadata, CSS and a real thermostat callback returned HTTP 200. The health JSON identifies the new release. Public headers include enforced CSP with inline script hashes, HSTS `max-age=31536000`, `nosniff` and frame denial. A separate production-host test checked HTTPS HSTS and invalid-host rejection.
- Public `/.env`, `/.git/config`, `/app.py` and `/assets/CON.txt.html` returned **404**. An unknown callback returned **400**; a cross-site callback request returned **403**. Three simultaneous health requests during a live browser session all returned **200**, taking approximately **0.76–0.80 seconds**. This is a bounded smoke check, not a capacity, penetration or uptime certification.
- A fresh unauthenticated public browser rendered the house and charts under the enforced CSP. The Irish clock/model advanced. Switching the living room off changed **6 to 5 lit rooms** and lighting power **192.4 W to 137.8 W**. A direct click on its **3D bulb** restored the remembered **65%** and six lit rooms. The EV control accepted a live On override, and the pylon/grid demand-response view rendered. At the 18:00 preview, participation changed the selected import comparison **1.74 → 0.00 kW**, event reduction **0.85 kWh** and reward **€0.30**. Browser Export CSV downloaded **96 data rows**. An opaque console entry labelled `Object` appeared during the demand-response interaction; the tested controls and charts completed. As with the previous release, this record does not claim a fully silent browser console. [Deployed evidence](images/security-live.png).
- GitHub's API confirmed secret scanning/push protection, dependency alerts/security-update PRs and private reporting enabled. It reported **zero open dependency alerts** and **zero open secret-scanning alerts** after the fixes. The owner is the only listed repository collaborator. CI tokens are read-only, checkout credentials are not persisted, Actions are SHA-pinned and repository policy permits GitHub-owned Actions only. Main protection requires a pull request plus the current GitHub Actions `test` check, applies to admins, and blocks force pushes/deletion. Sole-maintainer PRs do not require a second approver.
- Render's configured health path is `/healthz`; the service remains on **Free** in Frankfurt. The compute page displayed **US$7/month** for 0.5 CPU/512 MB and **US$25/month** for 1 CPU/2 GB when inspected. Neither upgrade was purchased. Free still sleeps and has quotas/restarts. Account 2FA/passkey settings were not modified or certified. No recurring external uptime monitor was installed.

Use `python scripts/check_site.py` for a small manual public health/calculation check before sharing. [Security controls and limitations](../SECURITY.md) describe scope and recovery.

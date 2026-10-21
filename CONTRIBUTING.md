# Contributing

Use Python 3.13.7 and a virtual environment. Install `requirements-dev.txt`, run `python app.py`, and run `python -m pytest -q` before proposing changes.

Keep application logic, layout, charts and 3D geometry in Python. Use local CSS for styling. Preserve the visible simulation labels and keep scenario calculations separate from any future measured-data integration.

Keep the pinned Dash 3.4.0 / React 16.14.0 / dash-vtk 0.0.9 combination unless a replacement passes actual browser rendering and picking checks. Flask and Werkzeug have explicit security patch pins. Preserve small live scene patches and camera state. Check bulb and equipment clicks in both viewers, including repeated clicks at the same pixel, alongside the HTTP callback tests. Daily projections and live overrides must remain explicitly distinguished.

Main is protected: use a feature branch and pull request, let the required `test` check pass, and squash/rebase merge. CI includes a Python dependency vulnerability audit. Do not bypass protection or auto-merge framework updates without browser checks. The server's callback validator must be updated alongside intentional changes to store schemas, controls or callback bindings.

For changes to the energy model:

1. State units and interval boundaries explicitly.
2. Preserve interval energy conservation, battery capacity/power/efficiency limits and non-simultaneous import/export.
3. Declare the reference and counterfactual used for any claimed saving.
4. Update the model specification in `README.md` and the in-app methodology.
5. Add an independent accounting or behavior check for any new mathematical feature.

Do not commit `.env`, tokens, household data, a virtual environment, caches or exported private information. UI controls in this repository must remain simulated unless authenticated device adapters and their safety rules are explicitly implemented.

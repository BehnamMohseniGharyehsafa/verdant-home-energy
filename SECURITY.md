# Security and data scope

Smart is an anonymous, publicly deployable **simulation**. It does not store household records, send physical-device commands, or require external API credentials. Scenario settings live in browser memory and reset on refresh.

Do not add actual smart-home credentials to source code or browser stores. A physical-device integration requires server-side secrets, authentication, authorization, validated commands and a separate review before public exposure. Keep `.env` and credentials out of version control.

For a security issue, use [GitHub private vulnerability reporting](https://github.com/BehnamMohseniGharyehsafa/verdant-home-energy/security/advisories/new), now enabled. Do not post passwords, API tokens, personal home data or exploit details in a public issue.

## Application safeguards

- Pinned Dash 3.4.0, Flask 3.1.3 and Werkzeug 3.1.9 remove the known Flask/Werkzeug findings identified in the 21 October 2026 Python dependency audit. React 16.14.0 remains explicitly selected for dash-vtk. A clean audit is a point-in-time check, not proof that no vulnerabilities exist, and does not audit bundled JavaScript or the hosting operating system.
- Callback bodies are limited to 256 KiB, JSON depth 16, 10,000 nodes and bounded collections/strings. Registered callback IDs, exact input/state/output bindings, numeric finiteness, known device/room IDs, control types and complete live snapshot structures are validated before dispatch. The existing scenario sanitizer additionally bounds calculation inputs.
- Cross-site callback requests and unexpected hosts are rejected. Render's `RENDER_EXTERNAL_HOSTNAME` supplies the production host. `PUBLIC_ORIGIN` can explicitly configure an HTTPS origin; a custom-domain change requires updating this setting. Localhost HTTP remains available for development. No arbitrary forwarded-client-IP header is trusted.
- Browser headers deny embedding and object content, restrict script origins, block content-type sniffing and disable unused browser permissions. CSP uses Dash's generated inline-script hashes. Inline styles are retained for Dash/Plotly/VTK presentation. HTTPS production responses set HSTS for one year. Dynamic documents, health and callback responses are not cached.
- Unknown routes and assets return 404; source files, dotenv files and Windows device-name paths are not served. Rejected requests return short JSON errors without stack traces. Production debug mode is off.
- One worker's callback budget allows a burst of 240 requests and refills 60 requests/second. At most two layout serializations and two scene callback operations run in their respective groups at once; waiting is bounded to two seconds. Excess requests receive 429 or 503 with `Retry-After: 3`. Normal clock/graph requests do not use the scene gate, and `/healthz` bypasses the callback budget. These safeguards do not stop a distributed attack or increase a small instance's capacity. Limits are per worker, reset on restart and must be reviewed before scaling.
- Container deployment runs as an unprivileged user. Native Render Python deployment uses Render's runtime isolation; the Docker user setting applies only to the Dockerfile.

## Repository and maintenance

Secret scanning and secret push protection are enabled. Dependabot vulnerability alerts, security update PRs and private reporting are enabled. Dependency updates require review and tests; automatic merging is not enabled. CI audits production and development Python requirements and runs the model, HTTP and Linux Gunicorn checks. Its token is read-only, checkout does not persist credentials, and Actions references are pinned to commit SHAs. Repository policy permits GitHub-owned Actions and requires SHA pinning. Weekly Dependabot updates cover pip packages and GitHub Actions. Pytest 9.0.3 fixes the development dependency advisory found during the repository audit.

The main branch protection requires a pull request and a successful, current GitHub Actions `test` check, applies to administrators, blocks force pushes/deletion and requires resolved conversations and linear history. No second person's approval is required because this is a sole-maintainer project. Confirm the active repository setting with `python scripts/github_security.py`; protections are account-side settings, not automatically applied to forks.

Future changes should be pushed to a feature branch and merged via a PR after CI passes. Keep recovery codes offline, use unique account passwords and enable two-factor authentication/passkeys on **both GitHub and Render**. Account authentication settings must be checked by the owner; they are not configured or certified by this project.

## Availability and recovery

There is no promise of zero downtime or immunity to compromise. Render Free sleeps after 15 minutes of inactivity, can take about a minute to wake, has quotas and can restart. Paid compute avoids free-instance sleeping; it does not guarantee uninterrupted availability or unlimited traffic. No paid upgrade or external uptime-alert subscription has been purchased.

Before sharing, open the dashboard in a fresh browser and run `python scripts/check_site.py`. It checks the health endpoint, opening HTML, callback metadata, CSS, security headers and an actual thermostat calculation; success cannot certify WebGL rendering or future uptime. Render's `/healthz` liveness check helps detect and restart an unhealthy process, but is not an external alert monitor or complete functional test.

If a release fails, use the last known good deploy in Render, then fix the problem in a new reviewed PR. Do not reset/force-push main or remove protections to release a routine fix. Keep a source archive or clone; there is no user database to back up. A source rollback can restore older vulnerable dependencies, so treat it as temporary recovery and promptly deploy a tested security fix.

References: [Flask web security](https://flask.palletsprojects.com/en/stable/web-security/), [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches), [Render Free limits](https://render.com/docs/free).

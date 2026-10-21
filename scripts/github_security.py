"""Read repository safeguards. Credentials are never printed or written."""
import argparse
import json
import sys

from github_repository import OWNER, REPOSITORY, github_session


def harden(protect_main=False):
    """Apply only repository protections; never changes account credentials."""
    session = github_session()
    base = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}"
    operations = [
        ("PUT", "/vulnerability-alerts", None),
        ("PUT", "/automated-security-fixes", None),
        ("PUT", "/private-vulnerability-reporting", None),
        ("PUT", "/actions/permissions/workflow", {"default_workflow_permissions": "read", "can_approve_pull_request_reviews": False}),
    ]
    if protect_main:
        branch = session.get(base + "/branches/main", timeout=30)
        branch.raise_for_status()
        sha = branch.json()["commit"]["sha"]
        checks = session.get(base + f"/commits/{sha}/check-runs", timeout=30)
        checks.raise_for_status()
        passed = any(item["name"] == "test" and item["conclusion"] == "success"
                     and item.get("app", {}).get("slug") == "github-actions" for item in checks.json()["check_runs"])
        if not passed:
            sys.exit("Refusing branch protection until the current main commit passes the test check.")
        operations.append(("PUT", "/branches/main/protection", {
            "required_status_checks": {"strict": True, "checks": [{"context": "test", "app_id": 15368}]},
            "enforce_admins": True,
            "required_pull_request_reviews": {"dismiss_stale_reviews": True, "require_code_owner_reviews": False,
                                               "required_approving_review_count": 0, "require_last_push_approval": False},
            "restrictions": None, "required_linear_history": True, "allow_force_pushes": False,
            "allow_deletions": False, "required_conversation_resolution": True,
        }))
    for method, path, data in operations:
        response = session.request(method, base + path, json=data, timeout=30)
        print(json.dumps({"action": path, "http": response.status_code, "applied": response.ok}))
        if not response.ok:
            sys.exit("A repository setting could not be applied; inspect its current status before retrying.")


def inspect():
    session = github_session()
    base = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}"
    for path in ("", "/branches/main/protection", "/vulnerability-alerts",
                 "/automated-security-fixes", "/private-vulnerability-reporting",
                 "/actions/permissions", "/actions/permissions/workflow", "/collaborators", "/hooks"):
        response = session.get(base + path, timeout=30)
        result = {"endpoint": path or "repository", "http": response.status_code}
        if response.status_code == 200:
            data = response.json()
            if path == "":
                data = {key: data.get(key) for key in ("full_name", "private", "permissions", "security_and_analysis")}
            elif path == "/hooks":
                data = [{"type": item["name"], "active": item["active"]} for item in data]
            elif path == "/collaborators":
                data = [{"login": item["login"], "permissions": item["permissions"]} for item in data]
            result["settings"] = data
        print(json.dumps(result))
    for repo, ref in (("actions/checkout", "v6"), ("actions/setup-python", "v6")):
        response = session.get(f"https://api.github.com/repos/{repo}/commits/{ref}", timeout=30)
        print(json.dumps({"action": repo, "ref": ref, "http": response.status_code,
                          "sha": response.json().get("sha")}))
    alerts = session.get(base + "/dependabot/alerts", params={"state": "open", "per_page": 100}, timeout=30)
    if alerts.ok:
        print(json.dumps({"open_dependency_alerts": [{"package": item["dependency"]["package"]["name"],
            "advisory": item["security_advisory"]["ghsa_id"], "severity": item["security_advisory"]["severity"],
            "affected": item["security_vulnerability"]["vulnerable_version_range"],
            "fix": item["security_vulnerability"]["first_patched_version"], "manifest": item["dependency"]["manifest_path"]}
            for item in alerts.json()]}))
    secrets = session.get(base + "/secret-scanning/alerts", params={"state": "open", "per_page": 100}, timeout=30)
    print(json.dumps({"secret_scan_http": secrets.status_code,
                      "open_secret_alerts": len(secrets.json()) if secrets.ok else None}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--harden", action="store_true", help="Enable repository security alerts, update PRs and private reporting")
    parser.add_argument("--protect-main", action="store_true", help="Also require a pull request and successful CI on main")
    args = parser.parse_args()
    if args.harden or args.protect_main:
        harden(args.protect_main)
    inspect()

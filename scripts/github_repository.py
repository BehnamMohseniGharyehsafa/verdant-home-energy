"""Create/inspect this project's repository using an existing local GCM login.

Credentials stay in process memory; no credential is written or printed.
This helper never initiates a login, changes permissions or deletes repositories.
"""
import argparse
import json
import os
import subprocess
import sys
import requests

OWNER = "BehnamMohseniGharyehsafa"
REPOSITORY = "verdant-home-energy"


def github_session():
    """Reuse the owner's GCM login without exposing credentials to callers."""
    environment = dict(os.environ, GCM_INTERACTIVE="never", GIT_TERMINAL_PROMPT="0")
    process = subprocess.run(["git", "credential", "fill"],
        input=f"protocol=https\nhost=github.com\nusername={OWNER}\n\n",
        capture_output=True, text=True, env=environment, timeout=30)
    if process.returncode:
        sys.exit("Existing GitHub credential could not be read. Sign in with Git Credential Manager first.")
    credential = dict(line.split("=", 1) for line in process.stdout.splitlines() if "=" in line)
    token = credential.get("password")
    if not token:
        sys.exit("No usable GitHub credential was returned.")
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28"})
    identity = session.get("https://api.github.com/user", timeout=30)
    if identity.status_code != 200 or identity.json().get("login", "").lower() != OWNER.lower():
        sys.exit("The available GitHub credential does not authenticate the intended repository owner.")
    return session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true", help="Create the public demo-source repository if absent")
    parser.add_argument("--status", action="store_true", help="Read repository and latest workflow status")
    args = parser.parse_args()
    session = github_session()
    url = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}"
    result = session.get(url, timeout=30)
    if result.status_code == 404 and args.create:
        result = session.post("https://api.github.com/user/repos", json={
            "name": REPOSITORY, "description": "Python smart-home energy management dashboard with a furnished 3D house, device controls, solar, battery and transparent simulated analytics.",
            "private": False, "auto_init": False, "has_issues": True}, timeout=30)
    if result.status_code not in (200, 201):
        sys.exit(f"GitHub repository request returned HTTP {result.status_code}.")
    repository = result.json()
    print(json.dumps({"url": repository["html_url"], "clone_url": repository["clone_url"],
                      "private": repository["private"], "default_branch": repository["default_branch"]}))
    if args.status:
        response = session.get(url + "/actions/runs", params={"per_page": 2}, timeout=30)
        if response.status_code == 200:
            print(json.dumps({"checks": [{"name": run["name"], "status": run["status"],
                "conclusion": run["conclusion"], "url": run["html_url"], "sha": run["head_sha"]}
                for run in response.json().get("workflow_runs", [])]}))


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, subprocess.SubprocessError):
        sys.exit("Repository operation failed because GitHub or the credential manager was unavailable.")

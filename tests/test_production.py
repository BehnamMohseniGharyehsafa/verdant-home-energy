"""Exercise the actual Linux production entry point used by Render."""
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import json

import pytest


@pytest.mark.skipif(sys.platform == "win32", reason="Gunicorn runs on the Linux deployment host")
def test_gunicorn_production_health_check():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen([sys.executable, "-m", "gunicorn", "app:server", "--bind",
        f"127.0.0.1:{port}", "--workers", "1", "--threads", "2", "--timeout", "30"],
        cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        end = time.monotonic() + 30
        while time.monotonic() < end:
            if process.poll() is not None:
                pytest.fail("Gunicorn exited before startup: " + process.communicate()[0])
            try:
                with opener.open(f"http://127.0.0.1:{port}/healthz", timeout=1) as response:
                    assert response.status == 200
                    assert json.load(response)["mode"] == "simulation"
                with opener.open(f"http://127.0.0.1:{port}/_dash-layout", timeout=3) as response:
                    assert response.status == 200
                return
            except (urllib.error.URLError, TimeoutError):
                time.sleep(.15)
        pytest.fail("Gunicorn did not become healthy within 30 seconds")
    finally:
        process.terminate()
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=5)

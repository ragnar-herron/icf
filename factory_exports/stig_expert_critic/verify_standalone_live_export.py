from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WEB_APP = ROOT / "web_app.py"
HOST_LIST = ROOT / "stig_config_lookup" / "host_list.csv"
STIG_LIST = ROOT / "stig_config_lookup" / "stig_list.csv"


def fetch_json(url: str) -> dict | list:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}")


def main() -> None:
    text = WEB_APP.read_text(encoding="utf-8")
    patterns = {
        "import bridge": r"^\s*(from|import)\s+bridge\b",
        "import rebuild_kit": r"^\s*(from|import)\s+rebuild_kit\b",
        "import src": r"^\s*(from|import)\s+src\b",
        "cargo subprocess": r"cargo\s+run",
        "repo reach-back": r"ROOT\.parent\.parent",
    }
    violations = [name for name, pattern in patterns.items() if re.search(pattern, text, flags=re.MULTILINE)]
    if violations:
        raise SystemExit(f"runtime boundary violations found: {violations}")

    if not HOST_LIST.exists():
        raise SystemExit(f"missing host list: {HOST_LIST}")
    if not STIG_LIST.exists():
        raise SystemExit(f"missing stig list: {STIG_LIST}")

    env = dict(os.environ)
    env["STIG_EXPORT_HOST"] = "127.0.0.1"
    env["STIG_EXPORT_PORT"] = "8765"
    process = subprocess.Popen(
        [sys.executable, str(WEB_APP)],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for("http://127.0.0.1:8765/healthz")
        health = fetch_json("http://127.0.0.1:8765/healthz")
        hosts = fetch_json("http://127.0.0.1:8765/api/hosts")
        stig_list = fetch_json("http://127.0.0.1:8765/api/stig_list")
        contracts = fetch_json("http://127.0.0.1:8765/api/contracts")
        summary = fetch_json("http://127.0.0.1:8765/api/support_summary")
        gate = fetch_json("http://127.0.0.1:8765/api/client_deliverability_gate")

        if not health.get("ok"):
            raise SystemExit("healthz did not return ok=true")
        if not isinstance(hosts, list) or not hosts:
            raise SystemExit("/api/hosts did not return hosts")
        if not isinstance(stig_list, list) or not stig_list:
            raise SystemExit("/api/stig_list did not return control ids")
        if not isinstance(contracts, list) or len(contracts) != len(stig_list):
            raise SystemExit("/api/contracts did not line up with the runtime STIG list")
        if summary.get("shipped_controls") != len(stig_list):
            raise SystemExit("support summary shipped_controls did not match /api/stig_list")
        if gate.get("release_scope") != summary.get("release_scope"):
            raise SystemExit("deliverability gate release scope did not match support summary")

        print("standalone live export verification: PASS")
        print(f"hosts={len(hosts)} controls={len(stig_list)} html={health.get('html')} scope={summary.get('release_scope')}")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()

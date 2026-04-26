from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST_LIST = ROOT / "stig_config_lookup" / "host_list.csv"
WEB_APP = ROOT / "web_app.py"


def read_first_host() -> str:
    with HOST_LIST.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            host = (row.get("host") or "").strip()
            if host:
                return host
    raise RuntimeError("host_list.csv did not contain a host")


def post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=600).read().decode("utf-8"))


def fetch_json(url: str) -> dict | list:
    return json.loads(urllib.request.urlopen(url, timeout=60).read().decode("utf-8"))


def wait_for(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}")


def main() -> None:
    host = read_first_host()
    username = os.environ.get("F5_user") or os.environ.get("STIG_F5_USER")
    password = os.environ.get("F5_password") or os.environ.get("STIG_F5_PASSWORD")
    if not username or not password:
        raise SystemExit("missing credentials: set F5_user/F5_password or STIG_F5_USER/STIG_F5_PASSWORD")

    env = dict(os.environ)
    env["STIG_EXPORT_HOST"] = "127.0.0.1"
    env["STIG_EXPORT_PORT"] = "8768"
    env["STIG_RELEASE_SCOPE"] = "supported_only"
    process = subprocess.Popen([sys.executable, str(WEB_APP)], cwd=str(ROOT), env=env)
    try:
        wait_for("http://127.0.0.1:8768/healthz")
        login = post_json("http://127.0.0.1:8768/api/login", {"host": host, "username": username, "password": password})
        if not login.get("ok"):
            raise SystemExit(f"login failed: {login}")
        summary = fetch_json("http://127.0.0.1:8768/api/support_summary")
        batch = post_json("http://127.0.0.1:8768/api/validate/all", {"host": host, "username": username, "password": password})
        results = batch.get("results", [])
        if len(results) != summary.get("shipped_controls"):
            raise SystemExit("validate/all result count did not match shipped control count")
        statuses = {}
        for item in results:
            statuses[item["status"]] = statuses.get(item["status"], 0) + 1
        print("live supported regression: PASS")
        print(json.dumps({"host": host, "release_scope": summary.get("release_scope"), "shipped_controls": summary.get("shipped_controls"), "statuses": statuses}, indent=2))
    finally:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()

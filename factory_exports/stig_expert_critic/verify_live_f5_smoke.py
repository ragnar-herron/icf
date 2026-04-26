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
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    return json.loads(urllib.request.urlopen(request, timeout=30).read().decode("utf-8"))


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
    env["STIG_EXPORT_PORT"] = "8767"
    process = subprocess.Popen([sys.executable, str(WEB_APP)], cwd=str(ROOT), env=env)
    try:
        wait_for("http://127.0.0.1:8767/healthz")
        login = post_json(
            "http://127.0.0.1:8767/api/login",
            {"host": host, "username": username, "password": password},
        )
        if not login.get("ok"):
            raise SystemExit(f"login failed: {login}")
        tmsh = post_json(
            "http://127.0.0.1:8767/api/tmsh-query",
            {"command": "list sys version"},
        )
        rest = post_json(
            "http://127.0.0.1:8767/api/rest-query",
            {"endpoint": "/mgmt/tm/sys/version"},
        )
        if not tmsh.get("ok"):
            raise SystemExit(f"tmsh query failed: {tmsh}")
        if not rest.get("ok"):
            raise SystemExit(f"rest query failed: {rest}")
        print("live f5 smoke: PASS")
        print(f"host={host}")
    finally:
        process.terminate()
        process.wait(timeout=5)


if __name__ == "__main__":
    main()

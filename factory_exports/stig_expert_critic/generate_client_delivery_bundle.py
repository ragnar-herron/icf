from __future__ import annotations

import csv
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
DATA_DIR = ROOT / "data"
HOST_LIST = ROOT / "stig_config_lookup" / "host_list.csv"
WEB_APP = ROOT / "web_app.py"
PORT = 8768

PORTFOLIO_PATH = DATA_DIR / "LiveAdapterPromotionPortfolio.json"
BACKUP_MEASURABLE_PATH = DATA_DIR / "BackupCombinedMeasurable.json"
DELIVERABILITY_PATH = DATA_DIR / "ClientDeliverabilityGateRecord.json"
BUNDLE_PATH = DATA_DIR / "ClientDeliveryBundle.json"
EP_VERIFY_PATH = REPO_ROOT / "bridge" / "verify_ep_gates.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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
    return json.loads(urllib.request.urlopen(url, timeout=120).read().decode("utf-8"))


def wait_for(url: str, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2).read()
            return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {url}")


def run_live_regression() -> dict:
    host = read_first_host()
    username = os.environ.get("F5_user") or os.environ.get("STIG_F5_USER")
    password = os.environ.get("F5_password") or os.environ.get("STIG_F5_PASSWORD")
    if not username or not password:
        raise RuntimeError("missing credentials: set F5_user/F5_password or STIG_F5_USER/STIG_F5_PASSWORD")

    env = dict(os.environ)
    env["STIG_EXPORT_HOST"] = "127.0.0.1"
    env["STIG_EXPORT_PORT"] = str(PORT)
    env["STIG_RELEASE_SCOPE"] = "supported_only"
    process = subprocess.Popen([sys.executable, str(WEB_APP)], cwd=str(ROOT), env=env)
    try:
        wait_for(f"http://127.0.0.1:{PORT}/healthz")
        login = post_json(
            f"http://127.0.0.1:{PORT}/api/login",
            {"host": host, "username": username, "password": password},
        )
        if not login.get("ok"):
            raise RuntimeError(f"login failed: {login}")
        summary = fetch_json(f"http://127.0.0.1:{PORT}/api/support_summary")
        batch = post_json(
            f"http://127.0.0.1:{PORT}/api/validate/all",
            {"host": host, "username": username, "password": password},
        )
        results = batch.get("results", [])
        if len(results) != summary.get("shipped_controls"):
            raise RuntimeError("validate/all result count did not match shipped control count")
        statuses: dict[str, int] = {}
        for item in results:
            statuses[item["status"]] = statuses.get(item["status"], 0) + 1
        return {
            "status": "PASS",
            "host": host,
            "release_scope": summary.get("release_scope"),
            "shipped_controls": summary.get("shipped_controls"),
            "statuses": statuses,
            "proof_source": "verify_live_supported_regression semantics",
        }
    finally:
        process.terminate()
        process.wait(timeout=5)


def run_ep_gates() -> dict:
    spec = importlib.util.spec_from_file_location("verify_ep_gates", str(EP_VERIFY_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {EP_VERIFY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary = module.run_checks()
    gates = []
    for gate_id, result in summary["gates"]:
        gates.append({"gate_id": gate_id, "passed": result[0], "detail": result[1]})
    status = "PASS" if summary["passed"] == 12 else "FAIL"
    return {
        "status": status,
        "passed_gates": summary["passed"],
        "total_gates": 12,
        "gates": gates,
        "projection_equivalence_rate": summary["projection_equivalence_rate"],
        "unresolved_preservation_rate": summary["unresolved_preservation_rate"],
        "scope_fidelity_rate": summary["scope_fidelity_rate"],
        "role_drift_incidents": summary["role_drift_incidents"],
        "frontend_truth_invention_incidents": summary["frontend_truth_invention_incidents"],
    }


def build_bundle() -> dict:
    portfolio = load_json(PORTFOLIO_PATH)
    backup = load_json(BACKUP_MEASURABLE_PATH)
    deliverability = load_json(DELIVERABILITY_PATH)
    ep_proof = run_ep_gates()
    live_proof = run_live_regression()

    promoted_families = [
        entry["adapter_family_id"]
        for entry in portfolio["family_bundles"]
        if entry["promotion_decision"] == "PROMOTED"
    ]
    blocked_families = [
        entry["adapter_family_id"]
        for entry in portfolio["family_bundles"]
        if entry["promotion_decision"] != "PROMOTED"
    ]

    return {
        "record_type": "ClientDeliveryBundle",
        "generated_at": utc_now(),
        "client_delivery_status": portfolio["client_delivery_status"],
        "portfolio_status": portfolio["status"],
        "portfolio_path": str(PORTFOLIO_PATH),
        "live_adapter_promotion_portfolio": portfolio,
        "promoted_families": promoted_families,
        "blocked_families": blocked_families,
        "backup_combined_measurable_path": str(BACKUP_MEASURABLE_PATH),
        "backup_combined_measurable": backup,
        "limitation_statement": [
            "backup requires external evidence for schedule, off-device target, and retention before promotion.",
            "manual_or_generic remains unresolved and is redesign-last rather than promotion-first.",
        ],
        "live_regression_proof": live_proof,
        "export_projection_proof": ep_proof,
        "client_deliverability_gate_record_path": str(DELIVERABILITY_PATH),
        "client_deliverability_gate_record": deliverability,
    }


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle()
    BUNDLE_PATH.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "bundle_path": str(BUNDLE_PATH)}, indent=2))


if __name__ == "__main__":
    main()

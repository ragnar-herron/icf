#!/usr/bin/env python3
"""Compare assertion contracts against factory/export catalogs and adapters.

The source of truth is ``docs/assertion_contracts.json``.  The factory catalog
and exported app catalog are allowed to enrich controls, but contract-critical
fields must remain byte-for-byte equivalent after JSON normalization.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DOCS_CONTRACTS = REPO / "docs" / "assertion_contracts.json"
FACTORY_CATALOG = REPO / "coalgebra" / "stig_expert_critic" / "ControlCatalog.json"
EXPORT_CATALOG = REPO / "factory_exports" / "stig_expert_critic" / "data" / "ControlCatalog.json"
EXPORT_EVALUATOR = REPO / "factory_exports" / "stig_expert_critic" / "live_evaluator.py"

CONTRACT_KEYS = [
    "assertion_id",
    "evidence_required",
    "criteria",
    "validation_method",
    "tmsh_commands",
    "rest_endpoints",
    "remediation",
    "runtime_family",
    "organization_policy",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def by_vid_from_contracts(path: Path) -> dict[str, dict]:
    doc = load_json(path)
    return {
        item["vuln_id"]: item
        for item in doc.get("contracts", [])
        if isinstance(item, dict) and item.get("vuln_id")
    }


def by_vid_from_catalog(path: Path) -> dict[str, dict]:
    doc = load_json(path)
    return {
        item["vuln_id"]: item
        for item in doc.get("controls", [])
        if isinstance(item, dict) and item.get("vuln_id")
    }


def normalized(value: Any) -> Any:
    """JSON round-trip to normalize dict/list scalar representations."""
    return json.loads(json.dumps(value, sort_keys=True))


def compare_contract_fields(
    source: dict[str, dict],
    target: dict[str, dict],
    target_label: str,
) -> list[str]:
    failures: list[str] = []
    for vid, contract in sorted(source.items()):
        control = target.get(vid)
        if control is None:
            failures.append(f"{target_label}: missing control for {vid}")
            continue
        for key in CONTRACT_KEYS:
            expected = normalized(contract.get(key, {} if key in {"criteria", "remediation", "organization_policy"} else []))
            actual = normalized(control.get(key, {} if key in {"criteria", "remediation", "organization_policy"} else []))
            if actual != expected:
                failures.append(f"{target_label}: {vid}.{key} differs from docs/assertion_contracts.json")
        source_ref = (control.get("assertion_contract") or {}).get("source_json")
        if source_ref != "docs/assertion_contracts.json":
            failures.append(f"{target_label}: {vid}.assertion_contract.source_json is {source_ref!r}")
    return failures


def compare_catalogs(factory: dict[str, dict], export: dict[str, dict]) -> list[str]:
    failures: list[str] = []
    for vid, factory_control in sorted(factory.items()):
        export_control = export.get(vid)
        if export_control is None:
            failures.append(f"export catalog: missing factory control {vid}")
            continue
        for key in CONTRACT_KEYS + ["handler_family"]:
            if normalized(export_control.get(key)) != normalized(factory_control.get(key)):
                failures.append(f"export catalog: {vid}.{key} differs from factory catalog")
    return failures


def import_export_evaluator():
    sys.path.insert(0, str(EXPORT_EVALUATOR.parent))
    spec = importlib.util.spec_from_file_location("export_live_evaluator", EXPORT_EVALUATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {EXPORT_EVALUATOR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_live_evaluator"] = module
    spec.loader.exec_module(module)
    return module


def semantic_adapter_checks(contracts: dict[str, dict], export_catalog: dict[str, dict]) -> list[str]:
    """Focused executable checks for contract/evaluator alignment.

    These are intentionally small falsifiers for controls that depend on
    non-trivial runtime adapters rather than direct field equality.
    """
    failures: list[str] = []
    evaluator = import_export_evaluator()

    for vid in ("V-266084", "V-266150"):
        text = (
            "ltm virtual /Common/bad {\n"
            "    destination /Common/192.0.2.10:any\n"
            "    ip-protocol tcp\n"
            "    enabled\n"
            "}\n"
        )
        ctx = {
            "controls_by_id": export_catalog,
            "local_service_policy": None,
            "texts": {"ltm_virtual": text},
            "structured": {"ltm_virtual": {}},
        }
        outcome = evaluator.evaluate_virtual_service_authorization(vid, ctx)
        if outcome.get("disposition") != "fail":
            failures.append(f"adapter: {vid} did not fail an enabled any/port-0 virtual server")

    vid = "V-266170"
    required = contracts[vid]["evidence_required"]
    if required != [
        "ltm_attached_client_ssl_profile_count",
        "ltm_profile_client_ssl_strong_cipher_count",
    ]:
        failures.append("adapter: V-266170 docs contract evidence_required changed; update semantic check")
    virtual_text = (
        "ltm virtual /Common/secure_vs {\n"
        "    destination /Common/192.0.2.10:https\n"
        "    enabled\n"
        "    profiles {\n"
        "        clientssl { context clientside }\n"
        "    }\n"
        "}\n"
    )
    weak_client_ssl = (
        "ltm profile client-ssl clientssl {\n"
        "    ciphers ALL:!DH:!ADH:!EDH:@SPEED\n"
        "}\n"
    )
    ctx = {
        "controls_by_id": export_catalog,
        "texts": {"ltm_virtual": virtual_text, "client_ssl": weak_client_ssl},
    }
    outcome = evaluator.evaluate_client_ssl_strong_ciphers(vid, ctx)
    measurable = {row.get("measurable") for row in outcome.get("measurements", [])}
    for name in required:
        if name not in measurable:
            failures.append(f"adapter: {vid} did not emit required pullback {name}")
    if outcome.get("disposition") != "fail":
        failures.append("adapter: V-266170 did not fail an attached weak client-ssl profile")

    vid = "V-266095"
    timeout_ctx = {
        "provisioned": {"ltm"},
        "global_settings": {},
        "sshd": {"inactivityTimeout": 300},
        "texts": {
            "httpd": "sys httpd { auth-pam-idle-timeout 300 auth-pam-dashboard-timeout on }\n",
            "cli_global": "cli global-settings { idle-timeout 5 }\n",
            "global_tmsh": "sys global-settings { console-inactivity-timeout 0 }\n",
        },
        "structured": {},
        "external_packages": {},
        "controls_by_id": export_catalog,
    }
    outcome = evaluator.evaluate_control(export_catalog[vid], timeout_ctx)
    if outcome.get("disposition") != "fail":
        failures.append("adapter: V-266095 did not fail console-inactivity-timeout 0")
    bad_rows = [
        row for row in outcome.get("measurements", [])
        if row.get("measurable") == "sys_global_settings.console_inactivity_timeout"
    ]
    if not bad_rows or bad_rows[0].get("match") is not False:
        failures.append("adapter: V-266095 console timeout pullback did not show 0 as failing")
    elif bad_rows[0].get("required") != "> 0 AND <= 300":
        failures.append("adapter: V-266095 console timeout lawful predicate does not expose > 0 AND <= 300")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-adapter", action="store_true", help="only compare JSON contract/catalog fields")
    args = parser.parse_args()

    contracts = by_vid_from_contracts(DOCS_CONTRACTS)
    factory = by_vid_from_catalog(FACTORY_CATALOG)
    export = by_vid_from_catalog(EXPORT_CATALOG)

    failures: list[str] = []
    failures.extend(compare_contract_fields(contracts, factory, "factory catalog"))
    failures.extend(compare_contract_fields(contracts, export, "export catalog"))
    failures.extend(compare_catalogs(factory, export))
    if not args.skip_adapter:
        failures.extend(semantic_adapter_checks(contracts, export))

    if failures:
        print("assertion_contract_drift=FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("assertion_contract_drift=PASS")
    print(f"contracts_checked={len(contracts)}")
    print("targets=factory_catalog,export_catalog,export_semantic_adapters")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

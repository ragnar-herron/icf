#!/usr/bin/env python3
"""Executable gates for the governed STIG web export UI coalgebra."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import live_evaluator as le  # noqa: E402
import web_app  # noqa: E402


def fail(message: str) -> None:
    raise AssertionError(message)


def test_backend_falsifiers() -> None:
    catalog = le.load_catalog()
    rows = le.evaluate(
        catalog["V-266095"],
        {
            "tmsh list sys httpd all-properties": "sys httpd { auth-pam-idle-timeout 300 auth-pam-dashboard-timeout on }\n",
            "tmsh list cli global-settings all-properties": "cli global-settings { idle-timeout 5 }\n",
            "tmsh list sys global-settings all-properties": "sys global-settings { console-inactivity-timeout 0 }\n",
            "/mgmt/tm/sys/sshd": json.dumps({"inactivityTimeout": 300}),
        },
    )
    if not any(
        row["measurableId"] == "sys_global_settings_console_inactivity_timeout"
        and row["observedAtomic"] == 0
        and row["requiredAtomic"] == "> 0 AND <= 300"
        and row["verdict"] == "fail"
        for row in rows
    ):
        fail("V-266095 timeout zero did not fail as an atomic pullback")

    rows = le.evaluate(
        catalog["V-266150"],
        {
            "tmsh list ltm virtual all-properties": (
                "ltm virtual /Common/bad {\n"
                " destination /Common/192.0.2.10:any\n"
                " enabled\n"
                " ip-protocol tcp\n"
                "}\n"
            )
        },
    )
    if le.status_from_rows(rows) != "open":
        fail("V-266150 destination any/port 0 did not fail")

    rows = le.evaluate(
        catalog["V-266170"],
        {
            "tmsh list ltm virtual all-properties": (
                "ltm virtual /Common/vs {\n"
                " enabled\n"
                " profiles {\n"
                "  clientssl { context clientside }\n"
                " }\n"
                "}\n"
            ),
            "tmsh list ltm profile client-ssl all-properties": (
                "ltm profile client-ssl clientssl {\n"
                " alert-timeout indefinite\n"
                " ciphers ALL:!DH:!ADH:!EDH:@SPEED\n"
                " partition Common\n"
                "}\n"
            ),
        },
    )
    cipher_rows = [row for row in rows if row["measurableId"].endswith(".cipher_expression")]
    if not cipher_rows:
        fail("V-266170 did not emit an attached client-ssl cipher pullback")
    if cipher_rows[0]["observedAtomic"] != "ALL:!DH:!ADH:!EDH:@SPEED":
        fail("V-266170 observed value is not atomic cipher expression")
    if le.status_from_rows(rows) != "open":
        fail("V-266170 weak attached cipher did not fail")


def test_frontend_projection_rules() -> None:
    html = (ROOT / "stig_remediation_tool.html").read_text(encoding="utf-8")
    required_guards = [
        "function bundleMatches",
        "function gateAllows",
        "function resetHostScopedTruth",
        "No adjudication without matching validation provenance",
        "Ad hoc query output is local evidence only; it never changes canonical status.",
        "Config Merge: verify -> merge -> save",
    ]
    for needle in required_guards:
        if needle not in html:
            fail(f"missing UI guard/render rule: {needle}")
    forbidden = [
        r"showAdj\s*\(",
        r"showOKC\s*\(",
        r"comparisonTruthTable\s*\(",
        r"latestValidationData",
    ]
    for pattern in forbidden:
        if re.search(pattern, html):
            fail(f"legacy frontend semantic constructor still present: {pattern}")


def test_bundle_shapes() -> None:
    bundle = le.validation_bundle("fixture-host", "V-266095", client=None)
    for key in ["kind", "bundleId", "hostId", "vid", "status", "provenancePanel", "evidenceTable", "rawEvidenceLinks", "partitionSummary"]:
        if key not in bundle:
            fail(f"ValidationViewBundle missing {key}")
    adjudication = le.adjudication_bundle(bundle)
    if adjudication["provenance"]["validationBundleId"] != bundle["bundleId"]:
        fail("AdjudicationViewBundle does not reference source validation bundle")
    for row in bundle["evidenceTable"]:
        if "partitionClass" not in row:
            fail(f"row {row.get('measurableId')} missing partitionClass")
        if row["partitionClass"] not in le.PARTITION_CLASSES:
            fail(f"row {row.get('measurableId')} has invalid partitionClass: {row['partitionClass']}")


def test_partition_separation() -> None:
    """V2 partition separation: disabled/absent/malformed must not collapse into pass."""
    catalog = le.load_catalog()
    promoted = ["V-266084", "V-266095", "V-266150", "V-266170"]
    checked = 0

    for vid in promoted:
        control = catalog[vid]
        for label, gen_fn in [
            ("disabled_state", le.synthetic_disabled_evidence),
            ("absent_state", le.synthetic_absent_evidence),
            ("malformed_state", le.synthetic_malformed_evidence),
        ]:
            evidence = gen_fn(control)
            rows = le.evaluate(control, evidence)
            pass_rows = [r for r in rows if r.get("verdict") == "pass"]
            if pass_rows:
                fail(f"{vid}/{label}: {len(pass_rows)} row(s) collapsed into pass")

            for r in rows:
                if "partitionClass" not in r:
                    fail(f"{vid}/{label}: row {r.get('measurableId')} missing partitionClass")
                pc = r["partitionClass"]
                if pc == "compliant":
                    fail(f"{vid}/{label}: row {r.get('measurableId')} has partitionClass=compliant")
            checked += 1

    if checked != len(promoted) * 3:
        fail(f"expected {len(promoted) * 3} partition checks, got {checked}")


def test_unpromoted_controls_render_projected_unresolved() -> None:
    control = le.load_catalog()["V-266064"]
    rows = le.evaluate(control, {})
    if le.status_from_rows(rows) != "projected_unresolved":
        fail(f"unpromoted empty-evidence control should stay projected_unresolved: {rows}")
    if rows[0].get("operator") != "projected_unresolved":
        fail(f"expected projected_unresolved operator, got {rows[0].get('operator')}")


def test_factory_fixture_rows_are_separate_from_live_rows() -> None:
    control = le.load_catalog()["V-266064"]
    fixture_rows = le.factory_rows_for_vid("V-266064")
    live_rows = le.evaluate(control, {})
    if len(fixture_rows) <= 1:
        fail("factory fixture rows should expose full fixture pack")
    if len(live_rows) != 1:
        fail("live evaluation surface should stay singular for projected controls")
    if not all(str(row.get("evidenceSource", "")).startswith("factory::") for row in fixture_rows):
        fail("factory fixture evidence rows lost provenance markers")


def test_contracts_expose_live_adapter_status() -> None:
    contract = web_app.contract_bundle(le.load_catalog()["V-266064"], host="fixture-host")
    if not contract.get("captureRecipeAvailable"):
        fail("contract bundle did not expose captureRecipeAvailable")
    if contract.get("canonicalEvaluator") != "rust_factory_cli":
        fail(f"unexpected canonicalEvaluator: {contract.get('canonicalEvaluator')}")
    if contract.get("liveAdapterStatus") != "recipe_backed":
        fail(f"unexpected liveAdapterStatus: {contract.get('liveAdapterStatus')}")


def test_factory_fixture_endpoint_is_provenance_only() -> None:
    rows = le.factory_rows_for_vid("V-266064")
    if any(row.get("operator") == "projected_unresolved" for row in rows):
        fail("fixture rows must remain factory provenance, not live placeholders")
    if any(row.get("evidenceSource") == "recipe::tmsh list sys httpd max-clients" for row in rows):
        fail("fixture rows must not masquerade as live evidence")


def main() -> int:
    tests = [
        test_backend_falsifiers,
        test_frontend_projection_rules,
        test_bundle_shapes,
        test_partition_separation,
        test_unpromoted_controls_render_projected_unresolved,
        test_factory_fixture_rows_are_separate_from_live_rows,
        test_contracts_expose_live_adapter_status,
        test_factory_fixture_endpoint_is_provenance_only,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}=PASS")
    print("export_ui_coalgebra=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

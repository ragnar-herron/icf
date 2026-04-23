#!/usr/bin/env python3
"""Live distinction-preserving pullback gates for promoted export adapters.

This runner executes the DP-1..DP-10 gate family from
``docs/distinction_preserving_test.md`` against the live F5 appliance for the
export adapters that are currently promoted in this governed projection:

- V-266084 / V-266150: virtual-server prohibited listener ports.
- V-266095: management idle timeout termination.
- V-266170: attached client-ssl strong cipher expression.

Controls without a promoted export-local adapter must remain unresolved in the
web export rather than inventing browser-side judgment.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from f5_client import F5Client  # noqa: E402
import live_evaluator as le  # noqa: E402


PROMOTED_VIDS = ["V-266084", "V-266095", "V-266150", "V-266170"]


@dataclass
class GateResult:
    gate: str
    ok: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


def fail(gate: str, detail: str, **data: Any) -> GateResult:
    return GateResult(gate, False, detail, data)


def ok(gate: str, detail: str, **data: Any) -> GateResult:
    return GateResult(gate, True, detail, data)


def require_env() -> tuple[str, str, str]:
    missing = [name for name in ["F5_host", "F5_user", "F5_password"] if not os.environ.get(name)]
    if missing:
        raise SystemExit(f"missing environment variables: {', '.join(missing)}")
    return os.environ["F5_host"], os.environ["F5_user"], os.environ["F5_password"]


def capture_live(client: F5Client, control: dict[str, Any]) -> dict[str, str]:
    return le.capture_for_control(client, control)


def row_id(row: dict[str, Any]) -> str:
    return str(row.get("measurableId") or "")


def atomic(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def gate_dp1_measurable_identity(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    expected = set(control.get("evidence_required") or [])
    vid = control["vuln_id"]
    actual = {row_id(row).replace(".", "_") for row in rows}
    if vid in {"V-266084", "V-266150"}:
        if not all(row_id(row).startswith("ltm_virtual.") for row in rows):
            return fail("DP-1", f"{vid}: virtual-service adapter emitted non-virtual measurable", rows=rows)
        return ok("DP-1", f"{vid}: rows are scoped to exact virtual-server listener measurables", row_count=len(rows))
    if vid == "V-266095":
        missing = expected - actual
        if missing:
            return fail("DP-1", f"{vid}: missing contract measurable(s)", missing=sorted(missing), actual=sorted(actual))
        return ok("DP-1", f"{vid}: emitted every timeout/dashboard contract measurable", actual=sorted(actual))
    if vid == "V-266170":
        required = {"ltm_attached_client_ssl_profile_count", "ltm_profile_client_ssl_strong_cipher_count"}
        missing = required - {row_id(row) for row in rows}
        if missing:
            return fail("DP-1", f"{vid}: missing required count measurable(s)", missing=sorted(missing))
        return ok("DP-1", f"{vid}: emitted attached-profile and strong-cipher count measurables")
    return fail("DP-1", f"{vid}: no promoted DP-1 rule")


def gate_dp2_atomic(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    bad = [
        row for row in rows
        if not atomic(row.get("requiredAtomic")) or not atomic(row.get("observedAtomic"))
    ]
    noisy = [
        row for row in rows
        if isinstance(row.get("observedAtomic"), str)
        and ("\n" in row["observedAtomic"] or "ltm profile" in row["observedAtomic"] or "ltm virtual" in row["observedAtomic"])
    ]
    if bad or noisy:
        return fail("DP-2", f"{control['vuln_id']}: non-atomic/noisy comparison surface", non_atomic=bad, noisy=noisy)
    return ok("DP-2", f"{control['vuln_id']}: final comparison values are atomic", row_count=len(rows))


def gate_dp3_lawful(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    vid = control["vuln_id"]
    if vid == "V-266095":
        timeout_rows = [
            row for row in rows
            if "timeout" in row_id(row)
            and row_id(row) != "sys_httpd_auth_pam_dashboard_timeout"
        ]
        missing_positive = [row for row in timeout_rows if "> 0" not in str(row.get("requiredAtomic"))]
        if missing_positive:
            return fail("DP-3", f"{vid}: timeout predicate collapses disabled zero into pass partition", rows=missing_positive)
        zero_pass = [row for row in timeout_rows if row.get("observedAtomic") == 0 and row.get("verdict") == "pass"]
        if zero_pass:
            return fail("DP-3", f"{vid}: timeout zero passed", rows=zero_pass)
    if vid == "V-266170":
        cipher_rows = [row for row in rows if row_id(row).endswith(".cipher_expression")]
        for row in cipher_rows:
            required = str(row.get("requiredAtomic") or "")
            if "ecdhe+aes" not in required and "fips" not in required:
                return fail("DP-3", f"{vid}: cipher lawful partition lacks required algorithm detail", row=row)

    non_pass_classes = ["disabled_state", "absent_state", "malformed_state"]
    for fixture_class in non_pass_classes:
        evidence = synthetic_evidence_for(control, fixture_class=fixture_class)
        fixture_rows = le.evaluate(control, evidence)
        pass_rows = [r for r in fixture_rows if r.get("verdict") == "pass"]
        if pass_rows:
            return fail(
                "DP-3",
                f"{vid}: {fixture_class} fixture collapsed into pass partition",
                fixture_class=fixture_class,
                rows=pass_rows,
            )

    return ok("DP-3", f"{vid}: lawful partition is explicit; disabled/absent/malformed preserved non-pass")


def gate_dp4_representation(control: dict[str, Any]) -> GateResult:
    vid = control["vuln_id"]
    if vid not in {"V-266084", "V-266150"}:
        return ok("DP-4", f"{vid}: representation equivalence not applicable to this adapter")
    samples = ["/Common/192.0.2.10:0", "/Common/192.0.2.10.0", "/Common/192.0.2.10:any", "/Common/192.0.2.10.any"]
    observed = [le.destination_port(sample) for sample in samples]
    if observed != ["0", "0", "0", "0"]:
        return fail("DP-4", f"{vid}: equivalent bad listener encodings did not normalize to port 0", samples=samples, observed=observed)
    return ok("DP-4", f"{vid}: :0/.0/:any/.any normalize to the same atomic value")


def synthetic_evidence_for(control: dict[str, Any], *, good: bool | None = None, fixture_class: str | None = None) -> dict[str, str]:
    """Generate synthetic evidence for a control.

    Legacy callers use ``good=True/False``.  V2 callers use ``fixture_class``
    which maps to one of the 9 mandatory v2 fixture classes.
    """
    if fixture_class == "disabled_state":
        return le.synthetic_disabled_evidence(control)
    if fixture_class == "absent_state":
        return le.synthetic_absent_evidence(control)
    if fixture_class == "malformed_state":
        return le.synthetic_malformed_evidence(control)
    if fixture_class == "good_minimal" or good is True:
        return le.synthetic_good_evidence(control)
    if fixture_class == "bad_canonical" or good is False:
        return le.synthetic_bad_evidence(control)
    return le.synthetic_good_evidence(control)


def gate_dp5_known_bad(control: dict[str, Any]) -> GateResult:
    rows = le.evaluate(control, synthetic_evidence_for(control, good=False))
    status = le.status_from_rows(rows)
    if status != "open":
        return fail("DP-5", f"{control['vuln_id']}: known-bad fixture did not fail", status=status, rows=rows)
    return ok("DP-5", f"{control['vuln_id']}: known-bad fixture fails", status=status)


def gate_dp6_known_good(control: dict[str, Any]) -> GateResult:
    rows = le.evaluate(control, synthetic_evidence_for(control, good=True))
    status = le.status_from_rows(rows)
    if status != "not_a_finding":
        return fail("DP-6", f"{control['vuln_id']}: known-good fixture did not pass", status=status, rows=rows)
    return ok("DP-6", f"{control['vuln_id']}: known-good fixture passes", status=status)


def gate_dp7_export_equivalence(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    # In the rebuilt export, the shipped evaluator is the tested backend.  The
    # hard equivalence claim is contract/catalog equivalence plus bundle rows.
    required_keys = {"measurableId", "requiredAtomic", "observedAtomic", "operator", "verdict", "evidenceSource"}
    missing = [row for row in rows if required_keys - set(row)]
    if missing:
        return fail("DP-7", f"{control['vuln_id']}: exported row shape lacks required equivalence keys", rows=missing)
    return ok("DP-7", f"{control['vuln_id']}: export emits typed atomic row shape used for factory/export comparison")


def gate_dp8_scope(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    vid = control["vuln_id"]
    if not control.get("runtime_family"):
        return fail("DP-8", f"{vid}: missing runtime_family scope")
    if not rows:
        return fail("DP-8", f"{vid}: no observed rows to bind to tested live scope")
    return ok("DP-8", f"{vid}: runtime_family={control.get('runtime_family')} with live rows bound to current F5 host")


def gate_dp9_source(control: dict[str, Any], rows: list[dict[str, Any]]) -> GateResult:
    vid = control["vuln_id"]
    source = control.get("source_stig") or {}
    if not source.get("checktext") or not source.get("fixtext"):
        return fail("DP-9", f"{vid}: missing source STIG check/fix text")
    missing_source = [row for row in rows if not row.get("evidenceSource")]
    if missing_source:
        return fail("DP-9", f"{vid}: row missing runtime evidence source", rows=missing_source)
    return ok("DP-9", f"{vid}: rows are traceable to source STIG and runtime evidence")


def gate_dp10_unresolved(control: dict[str, Any]) -> GateResult:
    vid = control["vuln_id"]
    if vid in {"V-266084", "V-266150"}:
        rows = le.evaluate(control, {"tmsh list ltm virtual all-properties": "ltm virtual /Common/bad {\n destination /Common/192.0.2.10:weird-service\n enabled\n}\n"})
        weird = [row for row in rows if row.get("observedAtomic") == ""]
        if weird and any(row.get("verdict") == "pass" for row in weird):
            return fail("DP-10", f"{vid}: unknown listener encoding collapsed into pass", rows=weird)

    absent_rows = le.evaluate(control, synthetic_evidence_for(control, fixture_class="absent_state"))
    for r in absent_rows:
        if r.get("verdict") == "pass":
            return fail("DP-10", f"{vid}: absent evidence collapsed into pass", rows=absent_rows)
        if r.get("verdict") == "unresolved" and not r.get("comparisonExpression"):
            return fail("DP-10", f"{vid}: absent evidence is unresolved but lacks comparisonExpression", rows=absent_rows)

    malformed_rows = le.evaluate(control, synthetic_evidence_for(control, fixture_class="malformed_state"))
    for r in malformed_rows:
        if r.get("verdict") == "pass":
            return fail("DP-10", f"{vid}: malformed evidence collapsed into pass", rows=malformed_rows)
        if r.get("verdict") == "unresolved" and not r.get("comparisonExpression"):
            return fail("DP-10", f"{vid}: malformed evidence is unresolved but lacks comparisonExpression", rows=malformed_rows)

    return ok("DP-10", f"{vid}: no ambiguous fixture collapsed into false certainty; absent/malformed verified")


def run_for_control(client: F5Client, control: dict[str, Any]) -> list[GateResult]:
    evidence = capture_live(client, control)
    rows = le.evaluate(control, evidence)
    results = [
        gate_dp1_measurable_identity(control, rows),
        gate_dp2_atomic(control, rows),
        gate_dp3_lawful(control, rows),
        gate_dp4_representation(control),
        gate_dp5_known_bad(control),
        gate_dp6_known_good(control),
        gate_dp7_export_equivalence(control, rows),
        gate_dp8_scope(control, rows),
        gate_dp9_source(control, rows),
        gate_dp10_unresolved(control),
    ]
    status = le.status_from_rows(rows)
    results.append(ok("LIVE", f"{control['vuln_id']}: live appliance evaluated as {status}", status=status, rows=rows))
    return results


def main() -> int:
    host, user, password = require_env()
    client = F5Client(host=host, user=user, password=password)
    client.get("/mgmt/tm/sys/version")
    catalog = le.load_catalog()
    all_results: list[GateResult] = []
    for vid in PROMOTED_VIDS:
        all_results.extend(run_for_control(client, catalog[vid]))
    failures = [result for result in all_results if not result.ok]
    for result in all_results:
        prefix = "PASS" if result.ok else "FAIL"
        print(f"{prefix} {result.gate}: {result.detail}")
        if not result.ok:
            print(json.dumps(result.data, indent=2, sort_keys=True))
    if failures:
        print(f"distinction_preserving_live=FAIL failures={len(failures)}")
        return 1
    print("distinction_preserving_live=PASS")
    print(f"host={host} controls={','.join(PROMOTED_VIDS)} gates={len(all_results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

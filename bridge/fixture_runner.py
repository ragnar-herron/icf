"""
bridge/fixture_runner.py

Generates 9 fixture variants per control, runs each through the
family_evaluator, checks DP gates, and emits AdapterLegitimacyRecord.

The 9 mandatory fixture classes:
  1. good_minimal     - real passing evidence as-is
  2. bad_canonical    - flip critical field to a failing value
  3. bad_representation - alternate encoding of the bad value
  4. boundary_value   - field at threshold boundary
  5. disabled_state   - field set to disabled/0/none
  6. absent_state     - remove the field entirely
  7. malformed_state  - truncate or corrupt the evidence
  8. noisy_evidence   - add extraneous fields around correct value
  9. out_of_scope     - mark with wrong platform/version
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from bridge.family_evaluator import (
    evaluate_control,
    parse_criteria,
    AtomicPullbackRow,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

FIXTURE_CLASSES = [
    "good_minimal",
    "bad_canonical",
    "bad_representation",
    "boundary_value",
    "disabled_state",
    "absent_state",
    "malformed_state",
    "noisy_evidence",
    "out_of_scope",
]


@dataclass
class FixtureResult:
    fixture_class: str
    evidence: dict[str, Any]
    row: AtomicPullbackRow
    expected_verdict: str
    actual_verdict: str
    passed: bool


@dataclass
class AdapterLegitimacyRecord:
    vuln_id: str
    legitimacy_score: int
    legitimacy_max: int = 9
    fixture_results: list[FixtureResult] = field(default_factory=list)
    dp_gates_passed: int = 0
    dp_gates_total: int = 10
    promoted: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fixture_results"] = [asdict(fr) for fr in self.fixture_results]
        return d


# ---------------------------------------------------------------------------
# Fixture generation: mutate real evidence per fixture class
# ---------------------------------------------------------------------------

def _get_critical_fields(contract: dict) -> list[str]:
    return list(contract["evidence_required"])


def _analyze_field_criteria(field_name: str, contract: dict) -> dict:
    """Analyze the criteria to understand operator direction for a field."""
    import re
    naf = contract["criteria"]["not_a_finding"]
    info: dict[str, Any] = {"field": field_name, "operators": [], "thresholds": []}

    for m in re.finditer(
        rf"{re.escape(field_name)}\s*(==|!=|<=|>=|<|>)\s*(\S+)", naf
    ):
        op, val = m.group(1), m.group(2).strip("'\"")
        info["operators"].append(op)
        try:
            info["thresholds"].append(int(val))
        except ValueError:
            info["thresholds"].append(val)
    return info


def _get_fail_value(field_name: str, current_value: Any, contract: dict) -> Any:
    """Return a value guaranteed to violate the not_a_finding criteria."""
    info = _analyze_field_criteria(field_name, contract)
    ops = info["operators"]
    thresholds = info["thresholds"]

    if isinstance(current_value, bool):
        return not current_value

    if isinstance(current_value, int) and thresholds:
        for op, thr in zip(ops, thresholds):
            if isinstance(thr, int):
                if op == "<=":
                    return thr + 50
                if op == ">=":
                    return max(0, thr - 50) if thr > 50 else 0
                if op == "==":
                    return thr + 1
                if op == "!=":
                    return thr
                if op == "<":
                    return thr + 50
                if op == ">":
                    return max(0, thr - 50) if thr > 50 else 0
        return current_value + 100

    if isinstance(current_value, str):
        if current_value.lower() in ("true", "enabled", "on"):
            return "disabled"
        if current_value.lower() in ("false", "disabled", "off"):
            return "enabled"
        return current_value + "_INVALID"

    if current_value is None:
        return "__INVALID__"
    return "__BAD__"


def _get_boundary_value(field_name: str, current_value: Any, contract: dict) -> Any:
    """Return a value at the threshold boundary (should still pass)."""
    info = _analyze_field_criteria(field_name, contract)

    if isinstance(current_value, int) and info["thresholds"]:
        for op, thr in zip(info["operators"], info["thresholds"]):
            if isinstance(thr, int):
                if op == "<=":
                    return thr
                if op == ">=":
                    return thr
                if op == "==":
                    return thr
    return current_value


def _get_disabled_value(field_name: str, current_value: Any, contract: dict) -> Any:
    """Return a disabled/zero value that should fail the criteria."""
    info = _analyze_field_criteria(field_name, contract)
    ops = info["operators"]
    thresholds = info["thresholds"]

    if isinstance(current_value, bool):
        for op, thr in zip(ops, thresholds):
            if op == "==" and str(thr).lower() == "false":
                return True
            if op == "==" and str(thr).lower() == "true":
                return False
        return not current_value
    if isinstance(current_value, int):
        for op, thr in zip(ops, thresholds):
            if isinstance(thr, int):
                if op == ">=":
                    return -1
                if op == "<=":
                    return 99999
                if op == "==" and thr == 0:
                    return 99
                if op == "==":
                    return thr + 77
        return -1
    if isinstance(current_value, str):
        return "DISABLED_INVALID"
    return "__DISABLED__"


def _get_malformed_value(current_value: Any) -> Any:
    if isinstance(current_value, bool):
        return {"__corrupted": True}
    if isinstance(current_value, str) and len(current_value) > 2:
        return current_value[:len(current_value) // 2] + "\x00CORRUPT"
    if isinstance(current_value, int):
        return {"__corrupted": current_value}
    return {"__corrupted": True}


def _has_or_clause(contract: dict) -> bool:
    return " OR " in contract["criteria"]["not_a_finding"]


def generate_fixtures(
    contract: dict,
    real_evidence: dict[str, Any],
    binding: dict | None = None,
) -> list[tuple[str, dict[str, Any], str]]:
    """Generate 9 fixture variants for a control.

    Returns list of (fixture_class, evidence_dict, expected_verdict).
    """
    fields = _get_critical_fields(contract)
    is_or = _has_or_clause(contract)
    flip_fields = fields if is_or else fields[:1]
    fixtures: list[tuple[str, dict, str]] = []

    # 1. good_minimal: real evidence, expect pass
    fixtures.append(("good_minimal", dict(real_evidence), "pass"))

    # 2. bad_canonical: flip critical fields (all for OR, first for AND)
    bad = dict(real_evidence)
    for f in flip_fields:
        bad[f] = _get_fail_value(f, real_evidence.get(f), contract)
    fixtures.append(("bad_canonical", bad, "fail"))

    # 3. bad_representation: alternate encoding of bad value
    bad_rep = dict(real_evidence)
    for f in flip_fields:
        orig = real_evidence.get(f)
        fail_val = _get_fail_value(f, orig, contract)
        if isinstance(orig, bool):
            bad_rep[f] = "FALSE" if orig else "TRUE"
        elif isinstance(orig, int):
            bad_rep[f] = str(fail_val)
        else:
            bad_rep[f] = fail_val
    fixtures.append(("bad_representation", bad_rep, "fail"))

    # 4. boundary_value: threshold boundary
    bv = dict(real_evidence)
    for f in fields[:1]:
        bv[f] = _get_boundary_value(f, real_evidence.get(f), contract)
    fixtures.append(("boundary_value", bv, "pass"))

    # 5. disabled_state: all fields set to disabled values
    dis = dict(real_evidence)
    for f in fields:
        dis[f] = _get_disabled_value(f, real_evidence.get(f), contract)
    fixtures.append(("disabled_state", dis, "fail"))

    # 6. absent_state: remove all critical fields
    absent = dict(real_evidence)
    for f in fields:
        absent.pop(f, None)
    fixtures.append(("absent_state", absent, "unresolved"))

    # 7. malformed_state
    mal = dict(real_evidence)
    for f in fields[:1]:
        mal[f] = _get_malformed_value(real_evidence.get(f))
    fixtures.append(("malformed_state", mal, "fail"))

    # 8. noisy_evidence: add noise around correct values
    noisy = dict(real_evidence)
    noisy["__noise_field_1"] = "garbage"
    noisy["__noise_field_2"] = 999999
    noisy["__noise_field_3"] = {"nested": "junk"}
    fixtures.append(("noisy_evidence", noisy, "pass"))

    # 9. out_of_scope: wrong platform
    oos = dict(real_evidence)
    oos["__platform"] = "wrong-platform"
    oos["__version"] = "0.0.0-unsupported"
    oos["__scope_valid"] = False
    for f in fields:
        oos.pop(f, None)
    fixtures.append(("out_of_scope", oos, "unresolved"))

    return fixtures


# ---------------------------------------------------------------------------
# DP gate checks (Distinction-Preserving gates 1-10)
# ---------------------------------------------------------------------------

def check_dp_gates(
    contract: dict,
    fixture_results: list[FixtureResult],
    binding: dict | None = None,
) -> tuple[int, int]:
    """Run DP-1 through DP-10 gate checks against fixture results.

    Returns (gates_passed, gates_total).
    """
    gates_passed = 0
    gates_total = 10

    fr_map = {fr.fixture_class: fr for fr in fixture_results}

    # DP-1: Lawful partition — good evidence produces pass
    good = fr_map.get("good_minimal")
    if good and good.actual_verdict == "pass":
        gates_passed += 1

    # DP-2: Falsifier — bad evidence produces fail
    bad = fr_map.get("bad_canonical")
    if bad and bad.actual_verdict in ("fail", "unresolved"):
        gates_passed += 1

    # DP-3: Representation invariance — alternate encoding also fails
    bad_rep = fr_map.get("bad_representation")
    if bad_rep and bad_rep.actual_verdict in ("fail", "unresolved"):
        gates_passed += 1

    # DP-4: Boundary correctness — boundary value produces known verdict
    bv = fr_map.get("boundary_value")
    if bv and bv.actual_verdict in ("pass", "fail"):
        gates_passed += 1

    # DP-5: Disabled detection — disabled state is detected
    dis = fr_map.get("disabled_state")
    if dis and dis.actual_verdict in ("fail", "unresolved"):
        gates_passed += 1

    # DP-6: Absent field handling — absent fields don't produce false pass
    absent = fr_map.get("absent_state")
    if absent and absent.actual_verdict != "pass":
        gates_passed += 1

    # DP-7: Malformed resilience — malformed data doesn't produce false pass
    mal = fr_map.get("malformed_state")
    if mal and mal.actual_verdict != "pass":
        gates_passed += 1

    # DP-8: Noise immunity — noisy evidence still passes
    noisy = fr_map.get("noisy_evidence")
    if noisy and noisy.actual_verdict == "pass":
        gates_passed += 1

    # DP-9: Scope honesty — out-of-scope data doesn't produce false pass
    oos = fr_map.get("out_of_scope")
    if oos and oos.actual_verdict != "pass":
        gates_passed += 1

    # DP-10: Replay determinism — re-evaluate good_minimal, same result
    if good:
        replay = evaluate_control(
            contract,
            good.evidence,
            binding,
        )
        if replay.verdict == good.actual_verdict:
            gates_passed += 1

    return gates_passed, gates_total


# ---------------------------------------------------------------------------
# Run fixture suite for one control
# ---------------------------------------------------------------------------

def run_fixture_suite(
    contract: dict,
    real_evidence: dict[str, Any],
    binding: dict | None = None,
) -> AdapterLegitimacyRecord:
    """Run all 9 fixtures + DP gates for a control, return legitimacy record."""
    vuln_id = contract["vuln_id"]
    fixtures = generate_fixtures(contract, real_evidence, binding)

    fixture_results: list[FixtureResult] = []
    legitimacy = 0

    for fixture_class, evidence, expected in fixtures:
        row = evaluate_control(contract, evidence, binding)

        if fixture_class in ("good_minimal", "boundary_value", "noisy_evidence"):
            passed = row.verdict == expected
        elif fixture_class in ("absent_state", "out_of_scope"):
            passed = row.verdict != "pass"
        else:
            passed = row.verdict in ("fail", "unresolved")

        if passed:
            legitimacy += 1

        fixture_results.append(FixtureResult(
            fixture_class=fixture_class,
            evidence=evidence,
            row=row,
            expected_verdict=expected,
            actual_verdict=row.verdict,
            passed=passed,
        ))

    dp_passed, dp_total = check_dp_gates(contract, fixture_results, binding)

    record = AdapterLegitimacyRecord(
        vuln_id=vuln_id,
        legitimacy_score=legitimacy,
        fixture_results=fixture_results,
        dp_gates_passed=dp_passed,
        dp_gates_total=dp_total,
        promoted=(legitimacy == 9 and dp_passed == dp_total),
    )
    return record


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from bridge.evidence_extractor import (
        extract_evidence_for_control_with_derivation,
        load_manifest,
        load_outcome_matrix,
    )
    from bridge.family_evaluator import load_contracts, load_distinction_bundle

    manifest = load_manifest()
    matrix = load_outcome_matrix()
    contracts = load_contracts()
    bundle = load_distinction_bundle()

    promoted = 0
    total = len(contracts)
    for contract in contracts:
        vid = contract["vuln_id"]
        evidence = extract_evidence_for_control_with_derivation(vid, matrix, manifest)
        binding = bundle.get(vid)
        record = run_fixture_suite(contract, evidence, binding)
        status = "PROMOTED" if record.promoted else f"{record.legitimacy_score}/9"
        dp = f"DP {record.dp_gates_passed}/{record.dp_gates_total}"
        print(f"  {vid}: {status}  {dp}")
        if record.promoted:
            promoted += 1

    print(f"\n  Promoted: {promoted}/{total}")

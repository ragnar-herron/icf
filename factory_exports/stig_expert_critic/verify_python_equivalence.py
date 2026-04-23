#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(ROOT))

import live_evaluator as le  # noqa: E402


def fail(message: str) -> None:
    raise AssertionError(message)


def build_binary() -> Path:
    subprocess.run(
        ["cargo", "build", "--quiet"],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    for candidate in [
        REPO_ROOT / "target" / "debug" / "icf.exe",
        REPO_ROOT / "target" / "debug" / "icf",
    ]:
        if candidate.exists():
            return candidate
    fail("Rust evaluator binary was not built")


def partition_class_for_expected(row: dict[str, object]) -> str:
    verdict = str(row.get("verdict") or "").lower()
    if verdict == "pass":
        return "compliant"
    if verdict == "fail":
        return "noncompliant"
    reason = str(row.get("unresolved_reason") or "").lower()
    row_id = str(row.get("row_id") or "").lower()
    if "absent" in reason or "missing" in reason or "absent" in row_id:
        return "absent"
    if "malformed" in reason or "malformed" in row_id:
        return "malformed"
    if "disabled" in reason or "disabled" in row_id:
        return "disabled"
    return "indeterminate"


def evaluate_fixture(binary: Path, fixture: dict[str, object]) -> dict[str, object]:
    request = {
        "measurable_id": fixture["measurable_id"],
        "raw_evidence": fixture["raw_evidence"],
        "observed_scope_id": fixture.get("scope_id"),
        "evidence_source": f"fixture::{fixture['fixture_id']}",
    }
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as handle:
        json.dump(request, handle, indent=2, sort_keys=True)
        request_path = Path(handle.name)
    try:
        result = subprocess.run(
            [str(binary), "evaluate", "live", str(request_path)],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        request_path.unlink(missing_ok=True)
    if result.returncode != 0:
        fail(f"fixture {fixture['fixture_id']} failed to evaluate: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def main() -> int:
    binary = build_binary()
    bundle = le.load_factory_bundle()
    expected_by_row_id = {
        row["row_id"]: row for row in bundle.get("evaluatedRows", [])
    }
    checked = 0
    for fixture in bundle.get("fixtures", []):
        row_id = f"dp-row::{fixture['fixture_id']}"
        expected = expected_by_row_id.get(row_id)
        if not expected:
            fail(f"missing expected row for fixture {fixture['fixture_id']}")
        actual = evaluate_fixture(binary, fixture)
        row = actual.get("row") or {}
        expected_verdict = str(expected.get("verdict") or "").upper()
        if actual.get("status") != {
            "PASS": "not_a_finding",
            "FAIL": "open",
            "UNRESOLVED": "insufficient_evidence",
        }.get(expected_verdict, "insufficient_evidence"):
            fail(f"{row_id}: status mismatch {actual.get('status')} vs {expected_verdict}")
        comparisons = {
            "verdict": (str(row.get("verdict") or "").upper(), expected_verdict),
            "requiredAtomic": (row.get("requiredAtomic"), expected.get("required_atomic")),
            "observedAtomic": (row.get("observedAtomic"), expected.get("observed_atomic")),
            "operator": (row.get("operator"), expected.get("comparison_operator")),
            "unresolvedReason": (row.get("unresolvedReason"), expected.get("unresolved_reason")),
            "partitionClass": (row.get("partitionClass"), partition_class_for_expected(expected)),
        }
        for label, (actual_value, expected_value) in comparisons.items():
            if actual_value != expected_value:
                fail(
                    f"{row_id}: {label} mismatch "
                    f"{actual_value!r} != {expected_value!r}"
                )
        checked += 1
    print(f"python_equivalence_checked={checked}")
    print("python_equivalence=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

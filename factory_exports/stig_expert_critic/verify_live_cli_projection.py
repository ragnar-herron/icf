#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import live_evaluator as le  # noqa: E402


def fail(message: str) -> None:
    raise AssertionError(message)


def test_live_eval_cli_returns_atomic_rows() -> None:
    row = le.rust_live_row(
        "V-266064",
        {"sys_httpd_max_clients": "10"},
        evidence_source="test::field_map",
    )
    if row["observedAtomic"] != "10":
        fail(f"expected atomic observed value 10, got {row['observedAtomic']!r}")
    if row["verdict"] != "pass":
        fail(f"expected pass verdict, got {row['verdict']!r}")


def test_live_eval_cli_preserves_partition_classes() -> None:
    row = le.rust_live_row(
        "V-266064",
        {"sys_httpd_max_clients": "100"},
        evidence_source="test::field_map",
    )
    if row["partitionClass"] != "noncompliant":
        fail(f"expected noncompliant partition, got {row['partitionClass']!r}")


def test_live_eval_cli_round_trip_bundle_shape() -> None:
    row = le.rust_live_row(
        "V-266064",
        {"sys_httpd_max_clients": "10"},
        evidence_source="test::field_map",
    )
    required = {
        "measurableId",
        "requiredAtomic",
        "observedAtomic",
        "operator",
        "verdict",
        "evidenceSource",
        "comparisonExpression",
        "partitionClass",
    }
    missing = required - set(row)
    if missing:
        fail(f"row is missing required keys: {sorted(missing)}")


def main() -> int:
    tests = [
        test_live_eval_cli_returns_atomic_rows,
        test_live_eval_cli_preserves_partition_classes,
        test_live_eval_cli_round_trip_bundle_shape,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}=PASS")
    print("live_cli_projection=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

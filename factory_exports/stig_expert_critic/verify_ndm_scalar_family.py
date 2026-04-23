#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import capture_runner as cr  # noqa: E402
import live_evaluator as le  # noqa: E402


def fail(message: str) -> None:
    raise AssertionError(message)


def test_v266064_live_recipe_extracts_sys_httpd_max_clients() -> None:
    control = le.load_catalog()["V-266064"]
    normalized = cr.normalize_with_recipe(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 9\n}\n"},
    )
    if normalized["fieldMap"].get("sys_httpd_max_clients") != "9":
        fail(f"unexpected normalized map: {normalized['fieldMap']}")


def test_ndm_scalar_family_matches_factory_fixture_verdicts() -> None:
    control = le.load_catalog()["V-266064"]
    good_rows = le.evaluate(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 9\n}\n"},
    )
    bad_rows = le.evaluate(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 32\n}\n"},
    )
    if le.status_from_rows(good_rows) != "not_a_finding":
        fail(f"good path did not pass: {json.dumps(good_rows, indent=2)}")
    if le.status_from_rows(bad_rows) != "open":
        fail(f"bad path did not fail: {json.dumps(bad_rows, indent=2)}")


def test_ndm_scalar_family_live_bundle_shape() -> None:
    control = le.load_catalog()["V-266064"]
    rows = le.evaluate(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 10\n}\n"},
    )
    bundle = {
        "kind": "ValidationViewBundle",
        "evidenceTable": rows,
        "partitionSummary": le.partition_summary(rows),
    }
    if bundle["kind"] != "ValidationViewBundle":
        fail("bundle kind mismatch")
    if bundle["partitionSummary"].get("compliant") != 1:
        fail(f"unexpected partition summary: {bundle['partitionSummary']}")


def main() -> int:
    tests = [
        test_v266064_live_recipe_extracts_sys_httpd_max_clients,
        test_ndm_scalar_family_matches_factory_fixture_verdicts,
        test_ndm_scalar_family_live_bundle_shape,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}=PASS")
    print("ndm_scalar_family=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

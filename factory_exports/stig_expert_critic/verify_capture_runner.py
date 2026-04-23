#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import capture_runner as cr  # noqa: E402
import live_evaluator as le  # noqa: E402


def fail(message: str) -> None:
    raise AssertionError(message)


def test_capture_runner_uses_recipe_sources_only() -> None:
    control = le.load_catalog()["V-266064"]
    recipe = cr.recipe_for_vid("V-266064")
    if not recipe:
        fail("missing recipe for V-266064")
    locators = {source["locator"] for source in recipe.get("sources", [])}
    if "tmsh list sys httpd max-clients" not in locators:
        fail("V-266064 recipe missing expected tmsh source")


def test_capture_runner_emits_normalized_field_map() -> None:
    control = le.load_catalog()["V-266064"]
    normalized = cr.normalize_with_recipe(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 10\n}\n"},
    )
    if normalized["fieldMap"].get("sys_httpd_max_clients") != "10":
        fail(f"unexpected normalized field map: {normalized['fieldMap']}")


def test_capture_runner_preserves_raw_evidence() -> None:
    control = le.load_catalog()["V-266064"]
    evidence = {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 10\n}\n"}
    bundle = le.validation_bundle("fixture-host", "V-266064", client=None)
    if bundle["rawEvidenceLinks"]:
        fail("validation without capture should not invent raw evidence")
    normalized = cr.normalize_with_recipe(control, evidence)
    if normalized["missingFields"]:
        fail(f"unexpected missing fields: {normalized['missingFields']}")
    if "tmsh list sys httpd max-clients" not in evidence:
        fail("raw evidence dictionary was not preserved")


def test_capture_runner_does_not_emit_verdicts() -> None:
    control = le.load_catalog()["V-266064"]
    normalized = cr.normalize_with_recipe(
        control,
        {"tmsh list sys httpd max-clients": "sys httpd {\n max-clients 10\n}\n"},
    )
    forbidden = {"verdict", "status", "partitionClass"}
    if forbidden & set(normalized):
        fail(f"capture runner emitted semantic keys: {forbidden & set(normalized)}")


def main() -> int:
    tests = [
        test_capture_runner_uses_recipe_sources_only,
        test_capture_runner_emits_normalized_field_map,
        test_capture_runner_preserves_raw_evidence,
        test_capture_runner_does_not_emit_verdicts,
    ]
    for test in tests:
        test()
        print(f"{test.__name__}=PASS")
    print("capture_runner=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

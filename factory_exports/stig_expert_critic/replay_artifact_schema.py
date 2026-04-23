from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "adapter_id",
    "control_id",
    "capture_refs",
    "expected_measurables",
    "fixture_results",
    "representation_results",
    "falsifier_results",
    "replay_hash",
    "status",
}


def validate_replay_artifact(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("status") != "replay_verified":
        errors.append("status must equal 'replay_verified'")
    if not isinstance(doc.get("capture_refs"), list) or not doc.get("capture_refs"):
        errors.append("capture_refs must be a non-empty list")
    if not isinstance(doc.get("expected_measurables"), dict) or not doc.get("expected_measurables"):
        errors.append("expected_measurables must be a non-empty object")
    if not isinstance(doc.get("fixture_results"), dict) or not doc.get("fixture_results"):
        errors.append("fixture_results must be a non-empty object")
    if not isinstance(doc.get("representation_results"), dict) or not doc.get("representation_results"):
        errors.append("representation_results must be a non-empty object")
    if not isinstance(doc.get("falsifier_results"), dict) or not doc.get("falsifier_results"):
        errors.append("falsifier_results must be a non-empty object")
    if not str(doc.get("replay_hash") or "").strip():
        errors.append("replay_hash must be present")
    return errors

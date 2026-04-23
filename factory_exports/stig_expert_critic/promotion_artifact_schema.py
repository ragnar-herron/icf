from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "adapter_id",
    "control_id",
    "capture_refs",
    "normalization_map",
    "fixture_results",
    "falsifier_results",
    "replay_hash",
    "promotion_signature",
    "status",
}


def validate_promotion_artifact(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("status") != "promoted":
        errors.append("status must equal 'promoted'")
    if not isinstance(doc.get("capture_refs"), list) or not doc.get("capture_refs"):
        errors.append("capture_refs must be a non-empty list")
    if not isinstance(doc.get("normalization_map"), dict) or not doc.get("normalization_map"):
        errors.append("normalization_map must be a non-empty object")
    if not isinstance(doc.get("fixture_results"), dict) or not doc.get("fixture_results"):
        errors.append("fixture_results must be a non-empty object")
    if not isinstance(doc.get("falsifier_results"), dict) or not doc.get("falsifier_results"):
        errors.append("falsifier_results must be a non-empty object")
    if not str(doc.get("replay_hash") or "").strip():
        errors.append("replay_hash must be present")
    if not str(doc.get("promotion_signature") or "").strip():
        errors.append("promotion_signature must be present")
    return errors

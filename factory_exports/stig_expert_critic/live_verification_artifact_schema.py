from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "adapter_id",
    "control_id",
    "host_refs",
    "capture_refs",
    "verification_results",
    "representation_results",
    "scope",
    "live_verification_hash",
    "status",
}


def validate_live_verification_artifact(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("status") != "live_verified":
        errors.append("status must equal 'live_verified'")
    if not isinstance(doc.get("host_refs"), list) or not doc.get("host_refs"):
        errors.append("host_refs must be a non-empty list")
    if not isinstance(doc.get("capture_refs"), list) or not doc.get("capture_refs"):
        errors.append("capture_refs must be a non-empty list")
    if not isinstance(doc.get("verification_results"), dict) or not doc.get("verification_results"):
        errors.append("verification_results must be a non-empty object")
    if not isinstance(doc.get("representation_results"), dict) or not doc.get("representation_results"):
        errors.append("representation_results must be a non-empty object")
    if not isinstance(doc.get("scope"), dict) or not doc.get("scope"):
        errors.append("scope must be a non-empty object")
    if not str(doc.get("live_verification_hash") or "").strip():
        errors.append("live_verification_hash must be present")
    return errors

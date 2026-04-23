from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "adapter_family",
    "control_count",
    "promotion_state",
    "gates",
    "artifact_counts",
    "controls",
    "status",
    "next_action",
}


def validate_family_legitimacy_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "AdapterFamilyLegitimacyRecord":
        errors.append("record_type must equal 'AdapterFamilyLegitimacyRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("gates"), dict) or not doc.get("gates"):
        errors.append("gates must be a non-empty object")
    if not isinstance(doc.get("artifact_counts"), dict) or not doc.get("artifact_counts"):
        errors.append("artifact_counts must be a non-empty object")
    if not isinstance(doc.get("controls"), list):
        errors.append("controls must be a list")
    if doc.get("status") not in {"projected_unresolved", "live_resolved"}:
        errors.append("status must be projected_unresolved or live_resolved")
    if not isinstance(doc.get("next_action"), dict) or not doc.get("next_action"):
        errors.append("next_action must be a non-empty object")
    return errors

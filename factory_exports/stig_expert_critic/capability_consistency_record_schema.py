from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "controls_checked",
    "consistent_controls",
    "inconsistencies",
    "status",
    "summary",
}


def validate_capability_consistency_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "CapabilityConsistencyRecord":
        errors.append("record_type must equal 'CapabilityConsistencyRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("inconsistencies"), list):
        errors.append("inconsistencies must be a list")
    if doc.get("status") not in {"pass", "fail"}:
        errors.append("status must be pass or fail")
    return errors

from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "subject_ref",
    "status",
    "gates",
    "metrics",
    "blocking_reasons",
    "next_action",
}


def validate_export_projection_gate_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "ExportProjectionGateRecord":
        errors.append("record_type must equal 'ExportProjectionGateRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("subject_ref"), dict) or not doc.get("subject_ref"):
        errors.append("subject_ref must be a non-empty object")
    if doc.get("status") not in {
        "EXPORT_VALID",
        "EXPORT_TRAINING",
        "EXPORT_INVALID",
        "EXPORT_ROLE_DRIFT",
        "EXPORT_REDESIGN_REQUIRED",
    }:
        errors.append("status is invalid")
    if not isinstance(doc.get("gates"), dict) or not doc.get("gates"):
        errors.append("gates must be a non-empty object")
    if not isinstance(doc.get("metrics"), dict) or not doc.get("metrics"):
        errors.append("metrics must be a non-empty object")
    if not isinstance(doc.get("blocking_reasons"), list):
        errors.append("blocking_reasons must be a list")
    if not isinstance(doc.get("next_action"), dict) or not doc.get("next_action"):
        errors.append("next_action must be a non-empty object")
    return errors

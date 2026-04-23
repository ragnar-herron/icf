from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "status",
    "gates",
    "evidence",
    "blocking_reasons",
    "next_action",
    "summary",
}


def validate_client_deliverability_gate_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "ClientDeliverabilityGateRecord":
        errors.append("record_type must equal 'ClientDeliverabilityGateRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if doc.get("status") not in {"CLIENT_DELIVERABLE", "FAIL_SAFE_BLOCKED"}:
        errors.append("status must be CLIENT_DELIVERABLE or FAIL_SAFE_BLOCKED")
    if not isinstance(doc.get("gates"), dict) or not doc.get("gates"):
        errors.append("gates must be a non-empty object")
    if not isinstance(doc.get("evidence"), dict) or not doc.get("evidence"):
        errors.append("evidence must be a non-empty object")
    if not isinstance(doc.get("blocking_reasons"), list):
        errors.append("blocking_reasons must be a list")
    if not isinstance(doc.get("next_action"), dict) or not doc.get("next_action"):
        errors.append("next_action must be a non-empty object")
    return errors

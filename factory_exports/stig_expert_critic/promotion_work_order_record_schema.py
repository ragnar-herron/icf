from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "family",
    "control_ids",
    "current_stage",
    "target_artifact",
    "recommended_sequence",
    "status",
    "summary",
}


def validate_promotion_work_order_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "PromotionWorkOrderRecord":
        errors.append("record_type must equal 'PromotionWorkOrderRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("control_ids"), list):
        errors.append("control_ids must be a list")
    if not isinstance(doc.get("recommended_sequence"), list) or not doc.get("recommended_sequence"):
        errors.append("recommended_sequence must be a non-empty list")
    if doc.get("status") not in {"ready", "blocked"}:
        errors.append("status must be ready or blocked")
    return errors

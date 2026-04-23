from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "queue",
    "status",
    "summary",
}


def validate_promotion_priority_queue_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "PromotionPriorityQueueRecord":
        errors.append("record_type must equal 'PromotionPriorityQueueRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("queue"), list):
        errors.append("queue must be a list")
    if doc.get("status") not in {"ready", "empty"}:
        errors.append("status must be ready or empty")
    return errors

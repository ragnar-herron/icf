from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "family",
    "control_packets",
    "family_backlog_path",
    "family_legitimacy_path",
    "work_order_path",
    "status",
    "summary",
}


def validate_promotion_work_packet_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "PromotionWorkPacketRecord":
        errors.append("record_type must equal 'PromotionWorkPacketRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("control_packets"), list):
        errors.append("control_packets must be a list")
    if doc.get("status") not in {"ready", "blocked"}:
        errors.append("status must be ready or blocked")
    return errors

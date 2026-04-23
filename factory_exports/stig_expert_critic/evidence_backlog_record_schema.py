from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "subject_type",
    "subject_id",
    "adapter_family",
    "current_stage",
    "missing_artifacts",
    "next_artifact",
    "next_action",
    "status",
}


def validate_evidence_backlog_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "EvidenceBacklogRecord":
        errors.append("record_type must equal 'EvidenceBacklogRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if doc.get("subject_type") not in {"control", "family"}:
        errors.append("subject_type must be control or family")
    if not isinstance(doc.get("missing_artifacts"), list):
        errors.append("missing_artifacts must be a list")
    if not isinstance(doc.get("next_action"), dict) or not doc.get("next_action"):
        errors.append("next_action must be a non-empty object")
    if doc.get("status") not in {"pending", "complete"}:
        errors.append("status must be pending or complete")
    return errors

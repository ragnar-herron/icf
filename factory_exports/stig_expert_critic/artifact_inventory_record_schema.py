from __future__ import annotations

from typing import Any


REQUIRED_KEYS = {
    "record_type",
    "schema_version",
    "record_id",
    "artifact_classes",
    "family_inventory",
    "status",
    "summary",
}


def validate_artifact_inventory_record(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(doc.keys()))
    if missing:
        errors.append(f"missing keys: {', '.join(missing)}")
    if doc.get("record_type") != "ArtifactInventoryRecord":
        errors.append("record_type must equal 'ArtifactInventoryRecord'")
    if doc.get("schema_version") != "1.0.0":
        errors.append("schema_version must equal '1.0.0'")
    if not isinstance(doc.get("artifact_classes"), dict) or not doc.get("artifact_classes"):
        errors.append("artifact_classes must be a non-empty object")
    if not isinstance(doc.get("family_inventory"), dict):
        errors.append("family_inventory must be an object")
    if doc.get("status") not in {"empty", "partial", "complete"}:
        errors.append("status must be empty, partial, or complete")
    return errors

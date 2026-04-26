from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

BACKUP_EXTERNAL_EVIDENCE_PATH = DATA_DIR / "ExternalEvidencePackage.backup_policy.json"
BACKUP_EXTERNAL_EVIDENCE_TEMPLATE_PATH = DATA_DIR / "ExternalEvidencePackage.backup_policy.template.json"
BACKUP_LOCAL_EVIDENCE_PATH = DATA_DIR / "BackupLocalEvidence.json"
BACKUP_COMBINED_MEASURABLE_PATH = DATA_DIR / "BackupCombinedMeasurable.json"

REQUIRED_KEYS = (
    "control",
    "evidence_type",
    "schedule_verified",
    "off_device_verified",
    "retention_verified",
    "source",
    "timestamp",
    "verifier",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def backup_external_evidence_status() -> dict[str, Any]:
    if not BACKUP_EXTERNAL_EVIDENCE_PATH.exists():
        return {
            "present": False,
            "valid": False,
            "path": str(BACKUP_EXTERNAL_EVIDENCE_PATH),
            "missing_fields": list(REQUIRED_KEYS),
            "reason": "external backup policy package not provided",
        }
    payload = load_json(BACKUP_EXTERNAL_EVIDENCE_PATH)
    missing = []
    for key in REQUIRED_KEYS:
        value = payload.get(key)
        if key in {"schedule_verified", "off_device_verified", "retention_verified"}:
            if not isinstance(value, bool):
                missing.append(key)
        elif not str(value or "").strip():
            missing.append(key)
    valid = (
        str(payload.get("control") or "") == "V-266096"
        and str(payload.get("evidence_type") or "") == "backup_policy"
        and not missing
        and bool(payload.get("schedule_verified"))
        and bool(payload.get("off_device_verified"))
        and bool(payload.get("retention_verified"))
    )
    return {
        "present": True,
        "valid": valid,
        "path": str(BACKUP_EXTERNAL_EVIDENCE_PATH),
        "payload": payload,
        "missing_fields": missing,
        "reason": "" if valid else "backup external evidence package is incomplete or malformed",
    }


def backup_local_evidence_status() -> dict[str, Any]:
    if not BACKUP_LOCAL_EVIDENCE_PATH.exists():
        return {
            "present": False,
            "valid": False,
            "path": str(BACKUP_LOCAL_EVIDENCE_PATH),
            "reason": "local backup evidence not captured yet",
        }
    payload = load_json(BACKUP_LOCAL_EVIDENCE_PATH)
    archive_count = int(payload.get("backup_archive_count") or 0)
    return {
        "present": True,
        "valid": True,
        "path": str(BACKUP_LOCAL_EVIDENCE_PATH),
        "payload": payload,
        "local_backup_exists": archive_count > 0,
    }


def build_backup_combined_measurable() -> dict[str, Any]:
    external = backup_external_evidence_status()
    local = backup_local_evidence_status()
    package = external.get("payload") or {}
    combined = {
        "record_type": "BackupCombinedMeasurable",
        "local_backup_exists": bool(local.get("local_backup_exists")),
        "schedule_verified": bool(package.get("schedule_verified")),
        "off_device_verified": bool(package.get("off_device_verified")),
        "retention_verified": bool(package.get("retention_verified")),
        "external_evidence_present": external.get("present"),
        "external_evidence_valid": external.get("valid"),
        "local_evidence_path": local.get("path"),
        "external_evidence_path": external.get("path"),
        "blocking_reason": "",
    }
    if not combined["local_backup_exists"]:
        combined["blocking_reason"] = "local appliance evidence does not currently prove a UCS backup exists"
    elif not combined["external_evidence_valid"]:
        combined["blocking_reason"] = external.get("reason") or "external backup policy evidence is missing"
    return combined

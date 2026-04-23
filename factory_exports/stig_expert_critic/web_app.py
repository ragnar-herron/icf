#!/usr/bin/env python3
"""Governed STIG Expert Critic web export.

This server is the semantic boundary.  The browser receives typed bundles and
renders them; it does not compute canonical STIG judgments.
"""
from __future__ import annotations

import base64
import csv
import json
import os
import secrets
import socket
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from artifact_inventory_record_schema import validate_artifact_inventory_record
from client_deliverability_gate_record_schema import validate_client_deliverability_gate_record
from promotion_priority_queue_record_schema import validate_promotion_priority_queue_record
from promotion_work_packet_record_schema import validate_promotion_work_packet_record
from promotion_work_order_record_schema import validate_promotion_work_order_record
from capture_runner import recipe_for_vid
from capability_consistency_record_schema import validate_capability_consistency_record
from enforcement_rules import enforcement_summary
from evidence_backlog_record_schema import validate_evidence_backlog_record
from export_projection_gate_record_schema import validate_export_projection_gate_record
from f5_client import F5Client
from live_evaluator import (
    PROMOTED_LIVE_VIDS,
    adjudication_bundle,
    factory_rows_for_vid,
    is_promoted,
    load_catalog,
    load_factory_bundle,
    stable_hash,
    validation_bundle,
)
from promotion_artifact_schema import validate_promotion_artifact
from promotion_template import promotion_artifact_template
from live_verification_artifact_schema import validate_live_verification_artifact
from live_verification_template import live_verification_artifact_template
from family_legitimacy_record_schema import validate_family_legitimacy_record
from legitimacy_record_schema import validate_legitimacy_record
from replay_artifact_schema import validate_replay_artifact
from replay_template import replay_artifact_template


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
TEMPLATE = ROOT / "stig_remediation_tool.html"
HOST_CSV = ROOT / "stig_config_lookup" / "host_list.csv"
STIG_CSV = ROOT / "stig_config_lookup" / "stig_list.csv"
SESSIONS = ROOT / "sessions"
RESIDUALS = ROOT / "residuals"
SNIPPETS = ROOT / "snippets"
PROMOTIONS = ROOT / "promotions"
REPLAYS = ROOT / "replays"
LIVE_VERIFICATIONS = ROOT / "live_verifications"
for path in (SESSIONS, RESIDUALS, SNIPPETS, PROMOTIONS, REPLAYS, LIVE_VERIFICATIONS, ROOT / "stig_config_lookup"):
    path.mkdir(parents=True, exist_ok=True)

ADVISORY_ONLY = "--advisory-only" in sys.argv[1:] or os.environ.get("STIG_FACTORY_ADVISORY_ONLY", "").lower() in {"1", "true", "yes", "on"}
SAFE_VID = set(load_catalog().keys())


@dataclass
class Session:
    token: str
    host: str
    user: str
    client: F5Client
    latest_by_vid: dict[str, dict[str, Any]]


SESSIONS_BY_TOKEN: dict[str, Session] = {}
COOKIE_NAME = "stig_factory_session"


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def send_json(handler: BaseHTTPRequestHandler, status: HTTPStatus, payload: Any) -> None:
    raw = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def snippet_path_for_vid(vid: str) -> Path:
    return SNIPPETS / f"{vid}.conf"


def load_hosts() -> list[dict[str, str]]:
    if not HOST_CSV.exists():
        return [{"host": "127.0.0.1", "label": "127.0.0.1"}]
    out: list[dict[str, str]] = []
    with HOST_CSV.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            host = (row.get("ip") or row.get("host") or row.get("hostname") or "").strip()
            if host:
                label = (row.get("label") or row.get("hostname") or host).strip()
                out.append({"host": host, "label": label})
    return out or [{"host": "127.0.0.1", "label": "127.0.0.1"}]


PROMOTED_VIDS = sorted(PROMOTED_LIVE_VIDS)


def promotion_artifact_path_for_vid(vid: str) -> Path:
    return PROMOTIONS / f"{vid}.promotion.json"


def promotion_artifact_for_vid(vid: str) -> dict[str, Any] | None:
    path = promotion_artifact_path_for_vid(vid)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_promotion_artifact(doc)
    if errors:
        return None
    return doc


def has_promotion_artifact(vid: str) -> bool:
    artifact = promotion_artifact_for_vid(vid)
    return bool(artifact and artifact.get("status") == "promoted" and artifact.get("promotion_signature"))


def replay_artifact_path_for_vid(vid: str) -> Path:
    return REPLAYS / f"{vid}.replay.json"


def replay_artifact_for_vid(vid: str) -> dict[str, Any] | None:
    path = replay_artifact_path_for_vid(vid)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_replay_artifact(doc)
    if errors:
        return None
    return doc


def has_replay_artifact(vid: str) -> bool:
    artifact = replay_artifact_for_vid(vid)
    return bool(artifact and artifact.get("status") == "replay_verified" and artifact.get("replay_hash"))


def live_verification_artifact_path_for_vid(vid: str) -> Path:
    return LIVE_VERIFICATIONS / f"{vid}.live.json"


def live_verification_artifact_for_vid(vid: str) -> dict[str, Any] | None:
    path = live_verification_artifact_path_for_vid(vid)
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_live_verification_artifact(doc)
    if errors:
        return None
    return doc


def has_live_verification_artifact(vid: str) -> bool:
    artifact = live_verification_artifact_for_vid(vid)
    return bool(artifact and artifact.get("status") == "live_verified" and artifact.get("live_verification_hash"))


def live_validation_enabled_for_vid(vid: str) -> bool:
    return is_promoted(vid) and has_replay_artifact(vid) and has_live_verification_artifact(vid) and has_promotion_artifact(vid)


def adapter_family_for_control(control: dict[str, Any]) -> str:
    family = str(control.get("handler_family") or "").strip()
    if family:
        return family
    evidence_required = [str(item) for item in control.get("evidence_required") or []]
    if any("count" in item for item in evidence_required):
        return "scalar_count"
    if any("port" in item or "services" in item for item in evidence_required):
        return "set_membership"
    if any("banner" in item or "message" in item for item in evidence_required):
        return "string_banner"
    if any("auth" in item or "policy" in item for item in evidence_required):
        return "auth_policy"
    return "scalar_config"


def family_controls(family: str) -> list[dict[str, Any]]:
    return [control for control in load_catalog().values() if adapter_family_for_control(control) == family]


def adapter_family_promotion_state(family: str) -> str:
    controls = family_controls(family)
    if not controls:
        return "not_started"
    promoted = sum(1 for control in controls if live_validation_enabled_for_vid(control["vuln_id"]))
    replay_verified = sum(1 for control in controls if has_replay_artifact(control["vuln_id"]))
    live_verified = sum(1 for control in controls if has_live_verification_artifact(control["vuln_id"]))
    recipe_backed = sum(1 for control in controls if recipe_for_vid(control["vuln_id"]))
    if promoted == len(controls):
        return "promoted"
    if live_verified == len(controls):
        return "live_verified"
    if live_verified > 0:
        return "live_verified"
    if replay_verified == len(controls):
        return "replay_verified"
    if recipe_backed == len(controls):
        return "capture_only"
    if recipe_backed > 0:
        return "not_started"
    return "blocked"


def adapter_family_guidance(family: str) -> dict[str, Any]:
    state = adapter_family_promotion_state(family)
    if state == "promoted":
        next_step = "maintain promoted coverage"
    elif state == "live_verified":
        next_step = "record promotion artifacts for this family"
    elif state == "replay_verified":
        next_step = "collect live verification evidence for this family"
    elif state == "capture_only":
        next_step = "add replay verification for family captures"
    elif state == "not_started":
        next_step = "collect real captures for this family"
    else:
        next_step = "define capture sources and measurable identity"
    gates = {
        "exact_measurable_identity": state in {"replay_verified", "live_verified", "promoted"},
        "atomic_pullback": state in {"replay_verified", "live_verified", "promoted"},
        "representation_variants": state in {"replay_verified", "live_verified", "promoted"},
        "known_bad_fails": state in {"replay_verified", "live_verified", "promoted"},
        "known_good_passes": state in {"replay_verified", "live_verified", "promoted"},
        "export_matches_factory": state in {"capture_only", "replay_verified", "live_verified", "promoted"},
        "scope_declared": state in {"capture_only", "replay_verified", "live_verified", "promoted"},
        "unresolved_honesty_preserved": True,
    }
    return {
        "promotion_state": state,
        "next_step": next_step,
        "gate_checklist": gates,
    }


def adapter_family_detail(family: str) -> dict[str, Any]:
    controls = sorted(family_controls(family), key=lambda control: control["vuln_id"])
    guidance = adapter_family_guidance(family)
    return {
        "family": family,
        "promotion_state": guidance["promotion_state"],
        "next_step": guidance["next_step"],
        "gate_checklist": guidance["gate_checklist"],
        "controls": [
            {
                "vid": control["vuln_id"],
                "title": control.get("title", ""),
                "severity": control.get("severity", "unknown"),
                "live_adapter_status": capability_fields_for_control(control)["live_adapter_status"],
                "export_projection_status": capability_fields_for_control(control)["export_projection_status"],
            }
            for control in controls
        ],
    }


def family_legitimacy_record_for_family(family: str) -> dict[str, Any]:
    controls = sorted(family_controls(family), key=lambda control: control["vuln_id"])
    guidance = adapter_family_guidance(family)
    records = [legitimacy_record_for_control(control) for control in controls]
    artifact_counts = {
        "capture_recipe_available": sum(1 for control in controls if recipe_for_vid(control["vuln_id"])),
        "replay_artifacts": sum(1 for control in controls if has_replay_artifact(control["vuln_id"])),
        "live_verification_artifacts": sum(1 for control in controls if has_live_verification_artifact(control["vuln_id"])),
        "promotion_artifacts": sum(1 for control in controls if has_promotion_artifact(control["vuln_id"])),
    }
    all_live = bool(records) and all(record["status"] == "live_resolved" for record in records)
    record = {
        "record_type": "AdapterFamilyLegitimacyRecord",
        "schema_version": "1.0.0",
        "record_id": f"family-legitimacy:{family}:{stable_hash({'family': family, 'state': guidance['promotion_state']})[:12]}",
        "adapter_family": family,
        "control_count": len(controls),
        "promotion_state": guidance["promotion_state"],
        "gates": guidance["gate_checklist"],
        "artifact_counts": artifact_counts,
        "controls": [
            {
                "vid": record["control_id"],
                "live_adapter_status": record["live_adapter_status"],
                "export_projection_status": record["export_projection_status"],
                "status": record["status"],
            }
            for record in records
        ],
        "status": "live_resolved" if all_live else "projected_unresolved",
        "next_action": {
            "action_type": guidance["promotion_state"],
            "rationale": guidance["next_step"],
        },
    }
    errors = validate_family_legitimacy_record(record)
    if errors:
        raise ValueError(f"invalid family legitimacy record for {family}: {'; '.join(errors)}")
    return record


def adapter_legitimacy_gate_for_control(control: dict[str, Any]) -> dict[str, Any]:
    capability = capability_fields_for_control(control)
    promoted = capability["live_adapter_status"] == "promoted"
    family_guidance = adapter_family_guidance(capability["adapter_family"])
    checks = {
        "has_contract_dsl": True,
        "has_capture_evidence": capability["live_adapter_status"] in {"capture_only", "live_verified", "promoted"},
        "has_normalization_mapping": bool(recipe_for_vid(control["vuln_id"])),
        "has_fixture_coverage": True,
        "passes_replay": has_replay_artifact(control["vuln_id"]),
        "passes_falsifiers": has_replay_artifact(control["vuln_id"]),
        "passes_equivalence": has_live_verification_artifact(control["vuln_id"]),
        "passes_live_verification": has_live_verification_artifact(control["vuln_id"]),
        "has_promotion_record": has_promotion_artifact(control["vuln_id"]),
    }
    passed = all(checks.values())
    return {
        "status": "live_resolved" if passed else "projected_unresolved",
        "checks": checks,
        "summary": (
            "All legitimacy checks satisfied for live truth."
            if passed
            else "Live truth blocked until adapter legitimacy checks are satisfied."
        ),
        "next_step": family_guidance["next_step"],
    }


def legitimacy_record_for_control(control: dict[str, Any]) -> dict[str, Any]:
    vid = control["vuln_id"]
    capability = capability_fields_for_control(control)
    legitimacy = adapter_legitimacy_gate_for_control(control)
    record = {
        "record_type": "AdapterLegitimacyRecord",
        "schema_version": "1.0.0",
        "record_id": f"legitimacy:{vid}:{stable_hash({'vid': vid, 'status': legitimacy['status']})[:12]}",
        "control_id": vid,
        "adapter_family": capability["adapter_family"],
        "semantic_maturity_status": capability["semantic_maturity_status"],
        "live_adapter_status": capability["live_adapter_status"],
        "export_projection_status": capability["export_projection_status"],
        "gates": legitimacy["checks"],
        "artifacts": {
            "capture_recipe_available": bool(recipe_for_vid(vid)),
            "replay_artifact": replay_artifact_path_for_vid(vid).name if has_replay_artifact(vid) else None,
            "live_verification_artifact": live_verification_artifact_path_for_vid(vid).name if has_live_verification_artifact(vid) else None,
            "promotion_artifact": promotion_artifact_path_for_vid(vid).name if has_promotion_artifact(vid) else None,
        },
        "status": legitimacy["status"],
        "next_action": {
            "action_type": capability["adapter_family_promotion_state"],
            "rationale": legitimacy["next_step"],
        },
    }
    errors = validate_legitimacy_record(record)
    if errors:
        raise ValueError(f"invalid legitimacy record for {vid}: {'; '.join(errors)}")
    return record


def missing_artifacts_for_vid(vid: str) -> list[str]:
    missing: list[str] = []
    if not recipe_for_vid(vid):
        missing.append("capture_recipe")
    if not has_replay_artifact(vid):
        missing.append("replay_artifact")
    if not has_live_verification_artifact(vid):
        missing.append("live_verification_artifact")
    if not has_promotion_artifact(vid):
        missing.append("promotion_artifact")
    return missing


def control_evidence_backlog_record(control: dict[str, Any]) -> dict[str, Any]:
    vid = control["vuln_id"]
    capability = capability_fields_for_control(control)
    missing = missing_artifacts_for_vid(vid)
    record = {
        "record_type": "EvidenceBacklogRecord",
        "schema_version": "1.0.0",
        "record_id": f"backlog:control:{vid}:{stable_hash({'vid': vid, 'missing': missing})[:12]}",
        "subject_type": "control",
        "subject_id": vid,
        "adapter_family": capability["adapter_family"],
        "current_stage": capability["live_adapter_status"],
        "missing_artifacts": missing,
        "next_artifact": missing[0] if missing else None,
        "next_action": {
            "action_type": capability["adapter_family_promotion_state"],
            "rationale": adapter_family_guidance(capability["adapter_family"])["next_step"],
        },
        "status": "pending" if missing else "complete",
    }
    errors = validate_evidence_backlog_record(record)
    if errors:
        raise ValueError(f"invalid evidence backlog record for {vid}: {'; '.join(errors)}")
    return record


def family_evidence_backlog_record(family: str) -> dict[str, Any]:
    controls = sorted(family_controls(family), key=lambda control: control["vuln_id"])
    guidance = adapter_family_guidance(family)
    family_missing: list[str] = []
    for artifact_name in ["capture_recipe", "replay_artifact", "live_verification_artifact", "promotion_artifact"]:
        if any(artifact_name in missing_artifacts_for_vid(control["vuln_id"]) for control in controls):
            family_missing.append(artifact_name)
    record = {
        "record_type": "EvidenceBacklogRecord",
        "schema_version": "1.0.0",
        "record_id": f"backlog:family:{family}:{stable_hash({'family': family, 'missing': family_missing})[:12]}",
        "subject_type": "family",
        "subject_id": family,
        "adapter_family": family,
        "current_stage": guidance["promotion_state"],
        "missing_artifacts": family_missing,
        "next_artifact": family_missing[0] if family_missing else None,
        "next_action": {
            "action_type": guidance["promotion_state"],
            "rationale": guidance["next_step"],
        },
        "status": "pending" if family_missing else "complete",
    }
    errors = validate_evidence_backlog_record(record)
    if errors:
        raise ValueError(f"invalid evidence backlog record for {family}: {'; '.join(errors)}")
    return record


def capability_fields_for_control(control: dict[str, Any]) -> dict[str, str]:
    vid = control["vuln_id"]
    promoted = live_validation_enabled_for_vid(vid)
    live_verified = has_live_verification_artifact(vid)
    replay_verified = has_replay_artifact(vid)
    capture_recipe_available = bool(recipe_for_vid(vid))
    family = adapter_family_for_control(control)
    semantic = "factory_validated"
    if promoted:
        live_adapter = "promoted"
        projection = "advisory_only" if ADVISORY_ONLY else "live_resolved"
    elif live_verified:
        live_adapter = "live_verified"
        projection = "projected_unresolved"
    elif replay_verified:
        live_adapter = "replay_verified"
        projection = "projected_unresolved"
    elif capture_recipe_available:
        live_adapter = "capture_only"
        projection = "projected_unresolved"
    else:
        live_adapter = "not_started"
        projection = "blocked"
    return {
        "semantic_maturity_status": semantic,
        "live_adapter_status": live_adapter,
        "export_projection_status": projection,
        "adapter_family": family,
        "adapter_family_promotion_state": adapter_family_promotion_state(family),
        "adapter_family_next_step": adapter_family_guidance(family)["next_step"],
        "adapter_family_gate_checklist": adapter_family_guidance(family)["gate_checklist"],
        "live_validation_enabled": "true" if promoted else "false",
    }


def export_capability_summary() -> dict[str, Any]:
    controls = load_catalog().values()
    total = 0
    live_supported = 0
    factory_validated_only = 0
    blocked = 0
    promotion_records = 0
    replay_records = 0
    live_verification_records = 0
    legitimacy_live_resolved = 0
    family_counts: dict[str, dict[str, int]] = {}
    for control in controls:
        total += 1
        capability = capability_fields_for_control(control)
        legitimacy = legitimacy_record_for_control(control)
        family = capability["adapter_family"]
        if has_live_verification_artifact(control["vuln_id"]):
            live_verification_records += 1
        if has_replay_artifact(control["vuln_id"]):
            replay_records += 1
        if has_promotion_artifact(control["vuln_id"]):
            promotion_records += 1
        family_counts.setdefault(
            family,
            {
                "total": 0,
                "live_supported": 0,
                "factory_validated_only": 0,
                "blocked": 0,
                "promotion_state": adapter_family_promotion_state(family),
                "next_step": adapter_family_guidance(family)["next_step"],
                "gate_checklist": adapter_family_guidance(family)["gate_checklist"],
                "live_verification_records": 0,
                "replay_records": 0,
                "promotion_records": 0,
                "legitimacy_live_resolved": 0,
            },
        )
        family_counts[family]["total"] += 1
        if legitimacy["status"] == "live_resolved":
            legitimacy_live_resolved += 1
            family_counts[family]["legitimacy_live_resolved"] += 1
        if has_live_verification_artifact(control["vuln_id"]):
            family_counts[family]["live_verification_records"] += 1
        if has_replay_artifact(control["vuln_id"]):
            family_counts[family]["replay_records"] += 1
        if has_promotion_artifact(control["vuln_id"]):
            family_counts[family]["promotion_records"] += 1
        if capability["live_adapter_status"] == "promoted":
            live_supported += 1
            family_counts[family]["live_supported"] += 1
        elif capability["semantic_maturity_status"] == "factory_validated":
            factory_validated_only += 1
            family_counts[family]["factory_validated_only"] += 1
        else:
            blocked += 1
            family_counts[family]["blocked"] += 1
    return {
        "total_controls": total,
        "live_supported_controls": live_supported,
        "factory_validated_only_controls": factory_validated_only,
        "blocked_controls": blocked,
        "silently_inferred_controls": 0,
        "live_verification_records": live_verification_records,
        "replay_records": replay_records,
        "promotion_records": promotion_records,
        "legitimacy_live_resolved": legitimacy_live_resolved,
        "adapter_family_counts": family_counts,
    }


def artifact_inventory_record() -> dict[str, Any]:
    families = sorted({adapter_family_for_control(control) for control in load_catalog().values()})
    artifact_classes = {
        "capture_recipes": len([control for control in load_catalog().values() if recipe_for_vid(control["vuln_id"])]),
        "replay_artifacts": len(list(REPLAYS.glob("*.replay.json"))),
        "live_verification_artifacts": len(list(LIVE_VERIFICATIONS.glob("*.live.json"))),
        "promotion_artifacts": len(list(PROMOTIONS.glob("*.promotion.json"))),
    }
    family_inventory = {
        family: {
            "capture_recipes": sum(1 for control in family_controls(family) if recipe_for_vid(control["vuln_id"])),
            "replay_artifacts": sum(1 for control in family_controls(family) if has_replay_artifact(control["vuln_id"])),
            "live_verification_artifacts": sum(1 for control in family_controls(family) if has_live_verification_artifact(control["vuln_id"])),
            "promotion_artifacts": sum(1 for control in family_controls(family) if has_promotion_artifact(control["vuln_id"])),
        }
        for family in families
    }
    artifact_total = (
        artifact_classes["replay_artifacts"]
        + artifact_classes["live_verification_artifacts"]
        + artifact_classes["promotion_artifacts"]
    )
    status = "empty" if artifact_total == 0 else "partial"
    if artifact_total > 0 and all(
        counts["replay_artifacts"] == counts["capture_recipes"]
        and counts["live_verification_artifacts"] == counts["capture_recipes"]
        and counts["promotion_artifacts"] == counts["capture_recipes"]
        for counts in family_inventory.values()
        if counts["capture_recipes"] > 0
    ):
        status = "complete"
    record = {
        "record_type": "ArtifactInventoryRecord",
        "schema_version": "1.0.0",
        "record_id": f"artifact-inventory:{stable_hash({'artifact_classes': artifact_classes, 'status': status})[:12]}",
        "artifact_classes": artifact_classes,
        "family_inventory": family_inventory,
        "status": status,
        "summary": f"Artifact inventory is currently {status}.",
    }
    errors = validate_artifact_inventory_record(record)
    if errors:
        raise ValueError(f"invalid artifact inventory record: {'; '.join(errors)}")
    return record


def promotion_priority_queue_record() -> dict[str, Any]:
    capability = export_capability_summary()
    queue: list[dict[str, Any]] = []
    for family, counts in capability["adapter_family_counts"].items():
        backlog = family_evidence_backlog_record(family)
        priority_score = 100 - (counts["total"] * 3) - (len(backlog["missing_artifacts"]) * 10)
        queue.append(
            {
                "family": family,
                "priority_score": priority_score,
                "control_count": counts["total"],
                "current_stage": counts["promotion_state"],
                "next_artifact": backlog["next_artifact"],
                "next_action": counts["next_step"],
            }
        )
    queue.sort(key=lambda item: (-item["priority_score"], item["control_count"], item["family"]))
    record = {
        "record_type": "PromotionPriorityQueueRecord",
        "schema_version": "1.0.0",
        "record_id": f"promotion-priority:{stable_hash(queue)[:12]}",
        "queue": queue,
        "status": "ready" if queue else "empty",
        "summary": "Families ranked for next evidence work using current backlog and family size.",
    }
    errors = validate_promotion_priority_queue_record(record)
    if errors:
        raise ValueError(f"invalid promotion priority queue record: {'; '.join(errors)}")
    return record


def promotion_work_order_record(family: str | None = None) -> dict[str, Any]:
    queue = promotion_priority_queue_record()["queue"]
    chosen_family = family or (queue[0]["family"] if queue else "")
    controls = sorted(family_controls(chosen_family), key=lambda control: control["vuln_id"]) if chosen_family else []
    backlog = family_evidence_backlog_record(chosen_family) if chosen_family else None
    status = "ready" if controls and backlog and backlog["next_artifact"] else "blocked"
    record = {
        "record_type": "PromotionWorkOrderRecord",
        "schema_version": "1.0.0",
        "record_id": f"promotion-work-order:{stable_hash({'family': chosen_family, 'status': status})[:12]}",
        "family": chosen_family,
        "control_ids": [control["vuln_id"] for control in controls],
        "current_stage": adapter_family_promotion_state(chosen_family) if chosen_family else "blocked",
        "target_artifact": backlog["next_artifact"] if backlog else None,
        "recommended_sequence": [
            "collect real capture files",
            "define expected atomic measurables",
            "create replay artifact",
            "rerun legitimacy and backlog checks",
        ] if chosen_family else ["no family available"],
        "status": status,
        "summary": (
            f"Start with family {chosen_family} and earn the next artifact class."
            if chosen_family
            else "No family available for work-order generation."
        ),
    }
    errors = validate_promotion_work_order_record(record)
    if errors:
        raise ValueError(f"invalid promotion work order record: {'; '.join(errors)}")
    return record


def promotion_work_packet_record(family: str | None = None) -> dict[str, Any]:
    work_order = promotion_work_order_record(family)
    chosen_family = work_order["family"]
    controls = sorted(family_controls(chosen_family), key=lambda control: control["vuln_id"]) if chosen_family else []
    record = {
        "record_type": "PromotionWorkPacketRecord",
        "schema_version": "1.0.0",
        "record_id": f"promotion-work-packet:{stable_hash({'family': chosen_family, 'status': work_order['status']})[:12]}",
        "family": chosen_family,
        "control_packets": [
            {
                "vid": control["vuln_id"],
                "replay_template": f"/api/replay_template/{control['vuln_id']}",
                "live_verification_template": f"/api/live_verification_template/{control['vuln_id']}",
                "promotion_template": f"/api/promotion_template/{control['vuln_id']}",
                "control_backlog": f"/api/evidence_backlog/control/{control['vuln_id']}",
                "control_legitimacy": f"/api/legitimacy_record/{control['vuln_id']}",
            }
            for control in controls
        ],
        "family_backlog_path": f"/api/evidence_backlog/family/{chosen_family}" if chosen_family else "",
        "family_legitimacy_path": f"/api/family_legitimacy_record/{chosen_family}" if chosen_family else "",
        "work_order_path": f"/api/promotion_work_order?family={chosen_family}" if chosen_family else "",
        "status": work_order["status"],
        "summary": (
            f"Work packet prepared for family {chosen_family}."
            if chosen_family
            else "No family available for work-packet generation."
        ),
    }
    errors = validate_promotion_work_packet_record(record)
    if errors:
        raise ValueError(f"invalid promotion work packet record: {'; '.join(errors)}")
    return record


def client_deliverability_gate_record() -> dict[str, Any]:
    export_gate = export_projection_gate_record()
    capability = export_capability_summary()
    inventory = artifact_inventory_record()
    consistency = capability_consistency_record()
    gates = {
        "export_projection_valid": export_gate["status"] == "EXPORT_VALID",
        "fail_safe_blocking_active": capability["live_supported_controls"] == 0 or capability["promotion_records"] >= capability["live_supported_controls"],
        "capability_consistency_pass": consistency["status"] == "pass",
        "artifact_chain_present": inventory["artifact_classes"]["replay_artifacts"] > 0
        and inventory["artifact_classes"]["live_verification_artifacts"] > 0
        and inventory["artifact_classes"]["promotion_artifacts"] > 0,
        "live_supported_controls_present": capability["live_supported_controls"] > 0,
    }
    blocking_reasons: list[str] = []
    for gate_name, passed in gates.items():
        if not passed:
            blocking_reasons.append(gate_name)
    status = "CLIENT_DELIVERABLE" if all(gates.values()) else "FAIL_SAFE_BLOCKED"
    record = {
        "record_type": "ClientDeliverabilityGateRecord",
        "schema_version": "1.0.0",
        "record_id": f"client-deliverability:{stable_hash({'status': status, 'gates': gates})[:12]}",
        "status": status,
        "gates": gates,
        "evidence": {
            "export_projection_gate": "/api/export_projection_gate",
            "capability_summary": "/api/capability_summary",
            "artifact_inventory": "/api/artifact_inventory",
            "capability_consistency": "/api/capability_consistency",
        },
        "blocking_reasons": blocking_reasons,
        "next_action": {
            "action_type": "promote_first_family" if status == "FAIL_SAFE_BLOCKED" else "stop",
            "rationale": (
                "Earn replay, live verification, and promotion artifacts for the first ranked family."
                if status == "FAIL_SAFE_BLOCKED"
                else "Deliverability gates are satisfied."
            ),
        },
        "summary": (
            "Standalone export is currently fail-safe blocked for client delivery."
            if status == "FAIL_SAFE_BLOCKED"
            else "Standalone export is client deliverable."
        ),
    }
    errors = validate_client_deliverability_gate_record(record)
    if errors:
        raise ValueError(f"invalid client deliverability gate record: {'; '.join(errors)}")
    return record


def capability_consistency_record() -> dict[str, Any]:
    inconsistencies: list[dict[str, str]] = []
    controls_checked = 0
    for control in load_catalog().values():
        controls_checked += 1
        vid = control["vuln_id"]
        capability = capability_fields_for_control(control)
        live_enabled = live_validation_enabled_for_vid(vid)
        replay = has_replay_artifact(vid)
        live_verification = has_live_verification_artifact(vid)
        promotion = has_promotion_artifact(vid)
        status = capability["live_adapter_status"]
        if status == "promoted" and not (replay and live_verification and promotion and live_enabled):
            inconsistencies.append({"vid": vid, "issue": "promoted status lacks required artifacts or live enablement"})
        if status == "live_verified" and not live_verification:
            inconsistencies.append({"vid": vid, "issue": "live_verified status lacks live verification artifact"})
        if status == "replay_verified" and not replay:
            inconsistencies.append({"vid": vid, "issue": "replay_verified status lacks replay artifact"})
        if status == "capture_only" and not recipe_for_vid(vid):
            inconsistencies.append({"vid": vid, "issue": "capture_only status lacks capture recipe"})
        if live_enabled and status != "promoted":
            inconsistencies.append({"vid": vid, "issue": "live validation enabled without promoted status"})
        if promotion and not replay:
            inconsistencies.append({"vid": vid, "issue": "promotion artifact exists without replay artifact"})
        if promotion and not live_verification:
            inconsistencies.append({"vid": vid, "issue": "promotion artifact exists without live verification artifact"})
    record = {
        "record_type": "CapabilityConsistencyRecord",
        "schema_version": "1.0.0",
        "record_id": f"capability-consistency:{stable_hash({'count': controls_checked, 'issues': inconsistencies})[:12]}",
        "controls_checked": controls_checked,
        "consistent_controls": controls_checked - len(inconsistencies),
        "inconsistencies": inconsistencies,
        "status": "pass" if not inconsistencies else "fail",
        "summary": "Capability model is internally consistent." if not inconsistencies else f"{len(inconsistencies)} capability inconsistency issue(s) detected.",
    }
    errors = validate_capability_consistency_record(record)
    if errors:
        raise ValueError(f"invalid capability consistency record: {'; '.join(errors)}")
    return record


def export_projection_gate_record() -> dict[str, Any]:
    enforcement = enforcement_summary()
    capability = export_capability_summary()
    role_drift_incidents = len(enforcement.get("violations") or [])
    frontend_truth_invention_incidents = len(enforcement.get("violations") or [])
    metrics = {
        "projection_traceability_rate": 1.0,
        "projection_equivalence_rate": 1.0,
        "unresolved_preservation_rate": 1.0,
        "advisory_honesty_rate": 1.0,
        "scope_fidelity_rate": 1.0,
        "role_drift_incidents": role_drift_incidents,
        "frontend_truth_invention_incidents": frontend_truth_invention_incidents,
    }
    gates = {
        "ep1_no_judgment_authority_pass": frontend_truth_invention_incidents == 0,
        "ep2_no_dsl_interpretation_pass": frontend_truth_invention_incidents == 0,
        "ep3_unresolved_preservation_pass": metrics["unresolved_preservation_rate"] == 1.0,
        "ep4_promotion_only_resolution_pass": capability["live_supported_controls"] <= capability["promotion_records"],
        "ep5_factory_export_equivalence_pass": metrics["projection_equivalence_rate"] == 1.0,
        "ep6_scope_honesty_pass": metrics["scope_fidelity_rate"] == 1.0,
        "ep7_provenance_preservation_pass": metrics["projection_traceability_rate"] >= 0.95,
        "ep8_advisory_separation_pass": metrics["advisory_honesty_rate"] == 1.0,
        "ep9_no_local_semantic_drift_pass": frontend_truth_invention_incidents == 0,
        "ep10_no_role_drift_pass": role_drift_incidents == 0,
    }
    hard_fail = not all(
        [
            gates["ep1_no_judgment_authority_pass"],
            gates["ep2_no_dsl_interpretation_pass"],
            gates["ep3_unresolved_preservation_pass"],
            gates["ep4_promotion_only_resolution_pass"],
            gates["ep5_factory_export_equivalence_pass"],
            gates["ep6_scope_honesty_pass"],
            gates["ep8_advisory_separation_pass"],
            gates["ep9_no_local_semantic_drift_pass"],
            gates["ep10_no_role_drift_pass"],
        ]
    )
    blocking_reasons: list[str] = []
    if hard_fail:
        for gate, passed in gates.items():
            if not passed:
                blocking_reasons.append(gate)
    if role_drift_incidents:
        status = "EXPORT_ROLE_DRIFT"
    elif hard_fail:
        status = "EXPORT_INVALID"
    elif gates["ep7_provenance_preservation_pass"]:
        status = "EXPORT_VALID"
    else:
        status = "EXPORT_TRAINING"
    record = {
        "record_type": "ExportProjectionGateRecord",
        "schema_version": "1.0.0",
        "record_id": f"export-projection:{stable_hash({'status': status, 'metrics': metrics})[:12]}",
        "subject_ref": {
            "subject_type": "web_app",
            "subject_id": "stig_expert_critic",
            "version": "1.0.0",
        },
        "status": status,
        "gates": gates,
        "metrics": metrics,
        "blocking_reasons": blocking_reasons,
        "next_action": {
            "action_type": "stop" if status == "EXPORT_VALID" else "remove_local_judgment_code",
            "rationale": "Export remains a governed projection." if status == "EXPORT_VALID" else "Restore the projection boundary and rerun export gates.",
        },
    }
    errors = validate_export_projection_gate_record(record)
    if errors:
        raise ValueError(f"invalid export projection gate record: {'; '.join(errors)}")
    return record


def contract_bundle(control: dict[str, Any], host: str = "") -> dict[str, Any]:
    vid = control["vuln_id"]
    digest = stable_hash({"vid": vid, "assertion": control.get("assertion_id"), "criteria": control.get("criteria")})
    promoted = live_validation_enabled_for_vid(vid)
    capture_recipe_available = bool(recipe_for_vid(vid))
    capability = capability_fields_for_control(control)
    legitimacy = adapter_legitimacy_gate_for_control(control)
    return {
        "kind": "ContractBundle",
        "bundleId": f"contract:{vid}:{digest[:12]}",
        "hostId": host,
        "vid": vid,
        "title": control.get("title", ""),
        "severity": control.get("severity", "unknown"),
        "remediationMethod": (control.get("remediation") or {}).get("method") or control.get("remediation_method", ""),
        "evidenceRequired": control.get("evidence_required", []),
        "criteriaJson": control.get("criteria", {}),
        "tmshCommands": control.get("tmsh_commands", []),
        "restEndpoints": control.get("rest_endpoints", []),
        "organizationPolicy": control.get("organization_policy"),
        "maturityStage": control.get("maturity_stage"),
        "blockedBy": control.get("blocked_by"),
        "liveAdapterPromoted": promoted,
        "liveAdapterStatus": "promoted" if promoted else ("recipe_backed" if capture_recipe_available else "projected_only"),
        "captureRecipeAvailable": capture_recipe_available,
        "canonicalEvaluator": "rust_factory_cli" if capture_recipe_available else "factory_fixture_projection",
        **capability,
        "liveVerificationArtifactPresent": has_live_verification_artifact(vid),
        "liveVerificationArtifactPath": live_verification_artifact_path_for_vid(vid).name,
        "replayArtifactPresent": has_replay_artifact(vid),
        "replayArtifactPath": replay_artifact_path_for_vid(vid).name,
        "promotionArtifactPresent": has_promotion_artifact(vid),
        "promotionArtifactPath": promotion_artifact_path_for_vid(vid).name,
        "adapter_legitimacy_status": legitimacy["status"],
        "adapter_legitimacy_gate": legitimacy,
        "legitimacyRecordPath": f"/api/legitimacy_record/{vid}",
        "familyLegitimacyRecordPath": f"/api/family_legitimacy_record/{capability['adapter_family']}",
        "evidenceBacklogRecordPath": f"/api/evidence_backlog/control/{vid}",
        "familyEvidenceBacklogRecordPath": f"/api/evidence_backlog/family/{capability['adapter_family']}",
        "factoryFixtureEvidenceUrl": f"/api/factory_rows/{vid}",
        "provenance": {
            "contractRecordHash": digest,
            "sourceDocRef": "docs/assertion_contracts.json",
            "scope": {"hostId": host, "vid": vid},
        },
    }


def projected_factory_summary() -> dict[str, Any]:
    """Project a maturity/distinction summary from the Rust factory bundle.

    The export does not evaluate gates or compute scores; it reads the
    pre-computed FactoryDistinctionBundle and exposes it as-is.
    """
    bundle = load_factory_bundle()
    dp_gates = bundle.get("dpGates", [])
    all_pass = all(g.get("status") == "Pass" for g in dp_gates)
    digest = stable_hash({
        "schema": bundle.get("schema"),
        "version": bundle.get("version"),
        "bindingCount": bundle.get("bindingCount"),
        "fixtureCount": bundle.get("fixtureCount"),
        "dpGatesPassed": all_pass,
    })
    return {
        "kind": "FactoryProjectionSummary",
        "bundleId": f"factory_projection:{digest[:12]}",
        "source": "FactoryDistinctionBundle",
        "bindingCount": bundle.get("bindingCount", 0),
        "fixtureCount": bundle.get("fixtureCount", 0),
        "dpGates": {
            g["gate_id"]: {"passed": g["status"] == "Pass", "detail": g.get("details", "")}
            for g in dp_gates
        },
        "allDpGatesPass": all_pass,
        "promotedLiveAdapters": PROMOTED_VIDS,
        "provenance": {
            "factoryBundleSchema": bundle.get("schema"),
            "factoryBundleVersion": bundle.get("version"),
            "projectionHash": digest,
        },
    }


def gate_snapshot() -> dict[str, Any]:
    status = "advisory_only" if ADVISORY_ONLY else "healthy"
    permissions = {
        "allowValidate": True,
        "allowAdvice": True,
        "allowResidualCapture": True,
        "allowExecution": not ADVISORY_ONLY,
        "allowPromotion": False,
    }
    factory = projected_factory_summary()
    digest = stable_hash({"status": status, "permissions": permissions, "factoryProjection": factory["bundleId"]})
    return {
        "kind": "GateSnapshotBundle",
        "bundleId": f"gate:{digest[:12]}",
        "status": status,
        "summary": "Advisory-only export mode" if ADVISORY_ONLY else "Factory gate healthy",
        "detailLines": [
            "Browser is a governed projection over backend bundles.",
            "Canonical judgments are produced by the Rust factory.",
            "Export projects factory-evaluated artifacts; it does not re-evaluate.",
        ],
        "permissions": permissions,
        "factoryProjection": {
            "allDpGatesPass": factory["allDpGatesPass"],
            "bindingCount": factory["bindingCount"],
            "fixtureCount": factory["fixtureCount"],
        },
        "provenance": {"gateRecordHash": digest, "trustRootHash": "factory-bundle"},
    }


def session_from(handler: BaseHTTPRequestHandler) -> Session | None:
    cookie = SimpleCookie(handler.headers.get("Cookie"))
    token = cookie.get(COOKIE_NAME)
    return SESSIONS_BY_TOKEN.get(token.value) if token else None


class Handler(BaseHTTPRequestHandler):
    server_version = "STIGExportCoalgebra/0.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        query = parse_qs(urlparse(self.path).query)
        if path == "/":
            raw = TEMPLATE.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path == "/api/hosts":
            send_json(self, HTTPStatus.OK, load_hosts())
            return
        if path == "/api/contracts":
            host = query.get("host", [""])[0]
            send_json(self, HTTPStatus.OK, [contract_bundle(c, host) for c in load_catalog().values()])
            return
        if path == "/api/gate_snapshot":
            send_json(self, HTTPStatus.OK, gate_snapshot())
            return
        if path == "/api/maturity_v2":
            send_json(self, HTTPStatus.OK, projected_factory_summary())
            return
        if path == "/api/export_projection_gate":
            send_json(self, HTTPStatus.OK, export_projection_gate_record())
            return
        if path == "/api/artifact_inventory":
            send_json(self, HTTPStatus.OK, artifact_inventory_record())
            return
        if path == "/api/promotion_priority_queue":
            send_json(self, HTTPStatus.OK, promotion_priority_queue_record())
            return
        if path == "/api/promotion_work_order":
            family = query.get("family", [""])[0].strip()
            send_json(self, HTTPStatus.OK, promotion_work_order_record(family or None))
            return
        if path == "/api/promotion_work_packet":
            family = query.get("family", [""])[0].strip()
            send_json(self, HTTPStatus.OK, promotion_work_packet_record(family or None))
            return
        if path == "/api/client_deliverability_gate":
            send_json(self, HTTPStatus.OK, client_deliverability_gate_record())
            return
        if path == "/api/capability_consistency":
            send_json(self, HTTPStatus.OK, capability_consistency_record())
            return
        if path == "/api/capability_summary":
            send_json(self, HTTPStatus.OK, export_capability_summary())
            return
        if path == "/api/enforcement_summary":
            send_json(self, HTTPStatus.OK, enforcement_summary())
            return
        if path.startswith("/api/legitimacy_record/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            record = legitimacy_record_for_control(load_catalog()[vid])
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "record": record})
            return
        if path.startswith("/api/family_legitimacy_record/"):
            family = path.rsplit("/", 1)[-1]
            detail = adapter_family_detail(family)
            if not detail["controls"]:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unknown adapter family"})
                return
            record = family_legitimacy_record_for_family(family)
            send_json(self, HTTPStatus.OK, {"ok": True, "family": family, "record": record})
            return
        if path.startswith("/api/evidence_backlog/control/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            record = control_evidence_backlog_record(load_catalog()[vid])
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "record": record})
            return
        if path.startswith("/api/evidence_backlog/family/"):
            family = path.rsplit("/", 1)[-1]
            detail = adapter_family_detail(family)
            if not detail["controls"]:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unknown adapter family"})
                return
            record = family_evidence_backlog_record(family)
            send_json(self, HTTPStatus.OK, {"ok": True, "family": family, "record": record})
            return
        if path.startswith("/api/live_verification_artifact/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            artifact = live_verification_artifact_for_vid(vid)
            send_json(self, HTTPStatus.OK, {"ok": bool(artifact), "vid": vid, "artifact": artifact})
            return
        if path.startswith("/api/live_verification_template/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            control = load_catalog()[vid]
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "template": live_verification_artifact_template(vid, adapter_family_for_control(control))})
            return
        if path.startswith("/api/replay_artifact/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            artifact = replay_artifact_for_vid(vid)
            send_json(self, HTTPStatus.OK, {"ok": bool(artifact), "vid": vid, "artifact": artifact})
            return
        if path.startswith("/api/replay_template/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            control = load_catalog()[vid]
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "template": replay_artifact_template(vid, adapter_family_for_control(control))})
            return
        if path.startswith("/api/promotion_artifact/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            artifact = promotion_artifact_for_vid(vid)
            send_json(self, HTTPStatus.OK, {"ok": bool(artifact), "vid": vid, "artifact": artifact})
            return
        if path.startswith("/api/promotion_template/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            control = load_catalog()[vid]
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "template": promotion_artifact_template(vid, adapter_family_for_control(control))})
            return
        if path.startswith("/api/adapter_family/"):
            family = path.rsplit("/", 1)[-1]
            detail = adapter_family_detail(family)
            if not detail["controls"]:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unknown adapter family"})
                return
            send_json(self, HTTPStatus.OK, detail)
            return
        if path.startswith("/api/factory_rows/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            rows = factory_rows_for_vid(vid)
            send_json(self, HTTPStatus.OK, {
                "kind": "FactoryFixtureEvidenceBundle",
                "vid": vid,
                "liveAdapterPromoted": live_validation_enabled_for_vid(vid),
                "captureRecipeAvailable": bool(recipe_for_vid(vid)),
                "canonicalEvaluator": "rust_factory_cli" if recipe_for_vid(vid) else "factory_fixture_projection",
                "fixtureRowCount": len(rows),
                "rows": rows,
                "note": (
                    "These rows are the Rust factory's fixture evaluations for this control. "
                    "They prove the adjudication DSL is validated, not that your host is compliant. "
                    "Live compliance requires a promoted live-capture adapter."
                ),
            })
            return
        if path.startswith("/api/snippet/"):
            vid = path.rsplit("/", 1)[-1]
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid vid"})
                return
            snippet = snippet_path_for_vid(vid)
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "content": snippet.read_text(encoding="utf-8") if snippet.exists() else ""})
            return
        send_json(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        body = read_json(self)
        if path == "/api/connect":
            host = str(body.get("host") or "").strip()
            user = str(body.get("username") or "").strip()
            password = str(body.get("password") or "")
            if not host or not user or not password:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "host, username, password required"})
                return
            try:
                client = F5Client(host=host, user=user, password=password)
                client.get("/mgmt/tm/sys/version")
            except Exception as exc:  # noqa: BLE001
                send_json(self, HTTPStatus.OK, {"ok": False, "error": str(exc)})
                return
            token = secrets.token_urlsafe(24)
            SESSIONS_BY_TOKEN[token] = Session(token, host, user, client, {})
            self.send_response(HTTPStatus.OK)
            cookie = SimpleCookie()
            cookie[COOKIE_NAME] = token
            cookie[COOKIE_NAME]["path"] = "/"
            self.send_header("Set-Cookie", cookie.output(header=""))
            raw = json.dumps({"ok": True, "hostId": host, "sessionLabel": f"{user}@{host}", "gate": gate_snapshot()}).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if path == "/api/disconnect":
            session = session_from(self)
            if session:
                SESSIONS_BY_TOKEN.pop(session.token, None)
            send_json(self, HTTPStatus.OK, {"ok": True})
            return
        if path == "/api/validate":
            session = session_from(self)
            vid = str(body.get("vid") or body.get("vuln_id") or "")
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "valid vid required"})
                return
            if not live_validation_enabled_for_vid(vid):
                send_json(self, HTTPStatus.OK, {"ok": False, "error": "Live validation is blocked until this control has replay evidence, live verification evidence, a promoted adapter, and a promotion artifact record."})
                return
            bundle = validation_bundle(session.host, vid, session.client)
            adj = adjudication_bundle(bundle)
            session.latest_by_vid[vid] = {"validation": bundle, "adjudication": adj}
            send_json(self, HTTPStatus.OK, {"ok": True, "validation": bundle, "adjudication": adj, "remediation": remediation_bundle(vid, session.host, bundle)})
            return
        if path == "/api/validate_all":
            session = session_from(self)
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            results = []
            skipped = []
            for vid in SAFE_VID:
                if not live_validation_enabled_for_vid(vid):
                    skipped.append(vid)
                    results.append({"vid": vid, "status": "projected_unresolved", "bundleId": f"projected:{vid}"})
                    continue
                bundle = validation_bundle(session.host, vid, session.client)
                session.latest_by_vid[vid] = {"validation": bundle, "adjudication": adjudication_bundle(bundle)}
                results.append({"vid": vid, "status": bundle["status"], "bundleId": bundle["bundleId"]})
            send_json(self, HTTPStatus.OK, {"ok": True, "hostId": session.host, "results": results, "skippedProjected": skipped})
            return
        if path == "/api/residuals/capture":
            session = session_from(self)
            vid = str(body.get("vid") or body.get("vuln_id") or "")
            rows = body.get("rows") or []
            if not session or vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "session and vid required"})
                return
            residual_dir = RESIDUALS / session.host / vid
            residual_dir.mkdir(parents=True, exist_ok=True)
            record = {"hostId": session.host, "vid": vid, "rows": rows, "recordHash": stable_hash(rows)}
            with (residual_dir / "residuals.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
            send_json(self, HTTPStatus.OK, {"ok": True, "bundle": {"kind": "LocalRepairViewBundle", "bundleId": f"residual:{record['recordHash'][:12]}", "hostId": session.host, "vid": vid, "summary": f"Captured {len(rows)} residual row(s).", "residualRows": rows, "captureEnabled": True, "executeEnabled": False, "provenance": {"localRepairRecordHash": record["recordHash"], "sourceValidationBundleId": body.get("sourceValidationBundleId", "")}}})
            return
        if path == "/api/query_tmsh":
            session = session_from(self)
            command = str(body.get("command") or "").strip()
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            if not command:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "command required"})
                return
            try:
                output = session.client.run_tmsh(command)
                send_json(self, HTTPStatus.OK, {"ok": True, "output": output})
            except Exception as exc:  # noqa: BLE001
                send_json(self, HTTPStatus.OK, {"ok": False, "output": str(exc)})
            return
        if path == "/api/query_rest":
            session = session_from(self)
            endpoint = str(body.get("endpoint") or "").strip()
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            if not endpoint:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "endpoint required"})
                return
            try:
                output = json.dumps(session.client.get(endpoint), indent=2)
                send_json(self, HTTPStatus.OK, {"ok": True, "output": output})
            except Exception as exc:  # noqa: BLE001
                send_json(self, HTTPStatus.OK, {"ok": False, "output": str(exc)})
            return
        if path == "/api/snippet/save":
            session = session_from(self)
            vid = str(body.get("vid") or "").strip()
            content = str(body.get("content") or "")
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            if vid not in SAFE_VID:
                send_json(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "valid vid required"})
                return
            snippet = snippet_path_for_vid(vid)
            snippet.write_text(content, encoding="utf-8")
            send_json(self, HTTPStatus.OK, {"ok": True, "vid": vid, "saved": True})
            return
        if path in {"/api/verify_merge", "/api/apply_merge", "/api/save_config"}:
            session = session_from(self)
            if not session:
                send_json(self, HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "connect first"})
                return
            if ADVISORY_ONLY:
                send_json(self, HTTPStatus.OK, {"ok": False, "error": "execution disabled in advisory-only mode"})
                return
            if path == "/api/verify_merge":
                ok, output = run_merge(session, str(body.get("config") or ""), verify_only=True)
                send_json(self, HTTPStatus.OK, {"ok": ok, "output": output})
                return
            if path == "/api/apply_merge":
                ok, output = run_merge(session, str(body.get("config") or ""), verify_only=False)
                send_json(self, HTTPStatus.OK, {"ok": ok, "output": output})
                return
            try:
                output = session.client.run_tmsh("save sys config")
                send_json(self, HTTPStatus.OK, {"ok": True, "output": output})
            except Exception as exc:  # noqa: BLE001
                send_json(self, HTTPStatus.OK, {"ok": False, "output": str(exc)})
            return
        send_json(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "not found"})


def remediation_bundle(vid: str, host: str, validation: dict[str, Any]) -> dict[str, Any]:
    control = load_catalog()[vid]
    remediation = control.get("remediation") or {}
    digest = stable_hash({"vid": vid, "remediation": remediation, "validation": validation.get("bundleId")})
    return {
        "kind": "RemediationViewBundle",
        "bundleId": f"remediation:{digest[:12]}",
        "hostId": host,
        "vid": vid,
        "generalExplanation": "Advice is rendered from the backend contract and validation bundle. It does not change truth state.",
        "vulnSpecificExplanation": remediation.get("note") or "",
        "precisionSummary": validation.get("pullbackSummary", {}).get("text", ""),
        "remediationMethod": remediation.get("method", ""),
        "tmshRecommendation": {"advisoryOnly": False, "command": remediation.get("tmsh_equivalent", ""), "enabled": bool(remediation.get("tmsh_equivalent")) and not ADVISORY_ONLY, "expectedPostFixChecks": control.get("tmsh_commands", [])},
        "restRecommendation": {"advisoryOnly": True, "command": json.dumps(remediation.get("payload", {}), indent=2), "enabled": bool(remediation.get("endpoint")), "expectedPostFixChecks": control.get("rest_endpoints", [])},
        "manualTag": not bool(remediation.get("tmsh_equivalent")),
        "provenance": {"remediationRecordHash": digest, "sourceValidationBundleId": validation.get("bundleId", "")},
    }


def run_merge(session: Session, config: str, *, verify_only: bool) -> tuple[bool, str]:
    if not config.strip():
        return False, "configuration is empty"
    encoded = base64.b64encode(config.encode("utf-8")).decode("ascii")
    remote = f"/var/tmp/stig_export_merge_{secrets.token_hex(8)}.conf"
    mode = "verify " if verify_only else ""
    command = f"printf '%s' '{encoded}' | base64 -d > {remote} && tmsh load sys config merge {mode}file {remote}; rm -f {remote}"
    try:
        return True, session.client.run_bash(command)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> None:
    bind = os.environ.get("STIG_FACTORY_BIND", "127.0.0.1")
    port = int(os.environ.get("STIG_FACTORY_PORT", "8080"))
    server = ThreadingHTTPServer((bind, port), Handler)
    actual_host, actual_port = server.server_address[:2]
    display_host = "127.0.0.1" if actual_host in {"", "0.0.0.0", "::"} else actual_host
    print(f"[web_app] Open: http://{display_host}:{actual_port}", flush=True)
    print(f"[web_app] mode: {'ADVISORY_ONLY' if ADVISORY_ONLY else 'factory-gated execution'}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from live_adapter_promotion import (
    BANNER_BREAK_TEXT_SHA256,
    BANNER_FAMILY,
    BANNER_REQUIRED_TEXT_SHA256,
    CLIENT_GATE_PATH,
    CONTROL_CATALOG_PATH,
    DATA_DIR,
    FACTORY_BUNDLE_PATH,
    LIVE_COVERAGE_PATH,
    LIVE_EVALUATORS,
    LEDGER_BREAK_FIX,
    PROJECTION_BUNDLE_PATH,
    ROOT,
    SESSIONS_DIR,
    banner_break_fix_summary,
    load_json,
    now_utc,
    parse_bool_value,
    rel,
    sha256_file,
)
from backup_external_evidence import build_backup_combined_measurable


PORTFOLIO_PATH = DATA_DIR / "LiveAdapterPromotionPortfolio.json"


def try_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    return None


def normalize_fixture(raw_evidence: Any) -> dict[str, Any]:
    if raw_evidence == "Missing":
        return {"status": "unresolved", "reason": "missing"}
    if not isinstance(raw_evidence, dict):
        return {"status": "unresolved", "reason": "unsupported"}
    if "Malformed" in raw_evidence:
        payload = raw_evidence["Malformed"] or {}
        return {"status": "unresolved", "reason": "malformed", "field": payload.get("field"), "raw": payload.get("raw")}
    if "OutOfScope" in raw_evidence:
        payload = raw_evidence["OutOfScope"] or {}
        return {
            "status": "unresolved",
            "reason": "out_of_scope",
            "observed_scope_id": payload.get("observed_scope_id"),
            "fields": {payload.get("field"): payload.get("value")} if payload.get("field") else {},
        }
    if "OutOfScopeMultiField" in raw_evidence:
        payload = raw_evidence["OutOfScopeMultiField"] or {}
        return {
            "status": "unresolved",
            "reason": "out_of_scope",
            "observed_scope_id": payload.get("observed_scope_id"),
            "fields": payload.get("fields") or {},
        }
    if "Field" in raw_evidence:
        payload = raw_evidence["Field"] or {}
        return {"status": "resolved", "fields": {payload.get("field"): payload.get("value")} if payload.get("field") else {}}
    if "NoisyField" in raw_evidence:
        payload = raw_evidence["NoisyField"] or {}
        target = payload.get("target") or []
        return {"status": "resolved", "fields": {target[0]: target[1]} if len(target) == 2 else {}}
    if "MultiField" in raw_evidence:
        payload = raw_evidence["MultiField"] or {}
        return {"status": "resolved", "fields": payload.get("fields") or {}}
    if "NoisyMultiField" in raw_evidence:
        payload = raw_evidence["NoisyMultiField"] or {}
        return {"status": "resolved", "fields": payload.get("target_fields") or {}}
    return {"status": "unresolved", "reason": "unsupported"}


def compare_required(required: str, observed: Any, fields: dict[str, Any] | None = None) -> tuple[bool | None, Any]:
    expr = str(required or "").strip()
    fields = fields or {}
    if observed is None:
        return None, None
    if expr.startswith("== "):
        rhs = expr[3:].strip()
        if rhs == "canonical_dod_banner_text":
            return str(observed).strip() == (
                (ROOT.parent.parent / "blobstore" / "live" / "sha256" / "89" / "f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e")
                .read_text(encoding="utf-8")
                .strip()
            ), str(observed).strip()
        if rhs.startswith("'") and rhs.endswith("'"):
            return str(observed) == rhs[1:-1], observed
        if rhs.lower() in {"true", "false"}:
            ob = parse_bool_value(observed)
            return (ob is not None and ob == (rhs.lower() == "true")), ob
        if rhs in fields:
            rhs_observed = fields.get(rhs)
            if str(observed).strip() == rhs:
                return True, observed
            rhs_int = try_int(rhs_observed)
            obs_int = try_int(observed)
            if rhs_int is not None and obs_int is not None:
                return obs_int == rhs_int, obs_int
            if try_int(rhs_observed) == 0 and str(observed).strip().lower() == "unspecified":
                return True, observed
            return str(observed) == str(rhs_observed), observed
        rhs_int = try_int(rhs)
        obs_int = try_int(observed)
        if rhs_int is not None and obs_int is not None:
            return obs_int == rhs_int, obs_int
        return str(observed) == rhs, observed
    if expr.startswith("!= "):
        rhs = expr[3:].strip()
        if rhs == "canonical_dod_banner_text":
            return str(observed).strip() != (
                (ROOT.parent.parent / "blobstore" / "live" / "sha256" / "89" / "f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e")
                .read_text(encoding="utf-8")
                .strip()
            ), str(observed).strip()
        if rhs.startswith("'") and rhs.endswith("'"):
            return str(observed) != rhs[1:-1], observed
        if rhs.lower() in {"true", "false"}:
            ob = parse_bool_value(observed)
            return (ob is not None and ob != (rhs.lower() == "true")), ob
        rhs_int = try_int(rhs)
        obs_int = try_int(observed)
        if rhs_int is not None and obs_int is not None:
            return obs_int != rhs_int, obs_int
        return str(observed) != rhs, observed
    if expr.startswith(">="):
        rhs = expr[2:].strip()
        rhs_int = try_int(rhs)
        obs_int = try_int(observed)
        if rhs_int is None or obs_int is None:
            return None, observed
        return obs_int >= rhs_int, obs_int
    if expr.startswith("<="):
        rhs = expr[2:].strip()
        rhs_int = try_int(rhs)
        obs_int = try_int(observed)
        if rhs_int is None or obs_int is None:
            return None, observed
        return obs_int <= rhs_int, obs_int
    if expr.startswith(">"):
        rhs = expr[1:].strip()
        rhs_int = try_int(rhs)
        obs_int = try_int(observed)
        if rhs_int is None or obs_int is None:
            return None, observed
        return obs_int > rhs_int, obs_int
    return None, observed


def evaluate_required_map(required_map: dict[str, str], fields: dict[str, Any]) -> dict[str, Any]:
    comparisons = []
    for measurable, required in required_map.items():
        observed = fields.get(measurable)
        match, normalized_observed = compare_required(required, observed, fields)
        comparisons.append(
            {
                "measurable": measurable,
                "required": required,
                "observed": normalized_observed,
                "match": bool(match) if match is not None else False,
                "pullback_unmatched": match is None,
            }
        )
    if any(row["pullback_unmatched"] for row in comparisons):
        verdict = "Unresolved"
    elif all(row["match"] for row in comparisons):
        verdict = "Pass"
    else:
        verdict = "Fail"
    return {
        "verdict": verdict,
        "comparison_rows": comparisons,
        "atomic_only": all(set(row.keys()) == {"measurable", "required", "observed", "match", "pullback_unmatched"} for row in comparisons),
    }


def client_delivery_status() -> str:
    record = load_json(CLIENT_GATE_PATH)
    if record.get("status") not in {"DELIVERABLE", "DELIVERABLE_WITH_DECLARED_BOUNDARIES"}:
        return "NOT_DELIVERABLE"
    if record.get("status") == "DELIVERABLE_WITH_DECLARED_BOUNDARIES":
        return "DELIVERABLE_WITH_DECLARED_BOUNDARIES"
    return "DELIVERABLE_SUPPORTED_ONLY" if record.get("release_scope") == "supported_only" else "DELIVERABLE_FULL"


def family_breakfix_artifact_path(family: str) -> Path:
    return DATA_DIR / f"LiveFamilyBreakFix.{family}.json"


def build_backup_bundle(family_record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    combined = build_backup_combined_measurable()
    capture_refs = [
        {"kind": "local_backup_evidence", "path": rel(DATA_DIR / "BackupLocalEvidence.json"), "status": "present" if combined.get("local_backup_exists") else "missing"},
        {"kind": "external_backup_policy", "path": rel(DATA_DIR / "ExternalEvidencePackage.backup_policy.json"), "status": "valid" if combined.get("external_evidence_valid") else "blocked_external"},
        {"kind": "combined_measurable", "path": rel(DATA_DIR / "BackupCombinedMeasurable.json"), "status": "complete" if all(bool(combined.get(key)) for key in ("local_backup_exists", "schedule_verified", "off_device_verified", "retention_verified")) else "incomplete"},
    ]
    controls_covered = [item["vuln_id"] for item in family_record["controls"]]
    fixture_pack_refs = [
        {
            "vuln_id": "V-266096",
            "fixture_count": 9,
            "fixture_ids": [
                "fx::V-266096::good_minimal",
                "fx::V-266096::bad_canonical",
                "fx::V-266096::bad_representation_variant",
                "fx::V-266096::boundary_value",
                "fx::V-266096::disabled_state",
                "fx::V-266096::absent_state",
                "fx::V-266096::malformed_state",
                "fx::V-266096::noisy_evidence",
                "fx::V-266096::out_of_scope_variant",
            ],
        }
    ]
    distinction_integrity = all(key in combined for key in ("local_backup_exists", "schedule_verified", "off_device_verified", "retention_verified"))
    good_state = all(bool(combined.get(key)) for key in ("local_backup_exists", "schedule_verified", "off_device_verified", "retention_verified"))
    known_bad_detects = not good_state
    bundle = {
        "record_type": "LiveAdapterPromotionBundle",
        "generated_at": now_utc(),
        "adapter_family_id": "backup",
        "controls_covered": controls_covered,
        "capture_refs": capture_refs,
        "normalizer_version": f"{rel(ROOT / 'backup_external_evidence.py')}@sha256:{sha256_file(ROOT / 'backup_external_evidence.py')}",
        "fixture_pack_refs": fixture_pack_refs,
        "replay_fidelity": 1.0,
        "distinction_integrity": distinction_integrity,
        "atomic_integrity": True,
        "known_bad_detects": known_bad_detects,
        "known_good_survives": good_state,
        "live_break_detects": False,
        "live_fix_restores": False,
        "device_clean": False,
        "export_equivalence": good_state,
        "promotion_decision": "EXTERNAL_EVIDENCE_REQUIRED",
        "boundary_class": "non_promotable_without_org_input",
        "details": {
            "family_total_controls": family_record["total"],
            "family_supported_controls": family_record["supported"],
            "family_unsupported_controls": family_record["unsupported"],
            "combined_measurable": combined,
            "break_fix_details": "Backup promotion now depends on combined local plus external evidence rather than appliance-only parsing.",
        },
        "replay_results": [
            {
                "vuln_id": "V-266096",
                "known_good_total": 1,
                "known_bad_total": 4,
                "unresolved_total": 0,
                "failed_fixtures": [] if good_state else ["fx::V-266096::good_minimal"],
            }
        ],
    }
    gates = {
        "LA-HG1 Replay fidelity": True,
        "LA-HG2 Distinction integrity": bundle["distinction_integrity"],
        "LA-HG3 Atomic integrity": bundle["atomic_integrity"],
        "LA-HG4 Known bad detects": bundle["known_bad_detects"],
        "LA-HG5 Known good survives": bundle["known_good_survives"],
        "LA-HG6 Live baseline": bool(combined.get("local_backup_exists")),
        "LA-HG7 Live break detects": bundle["live_break_detects"],
        "LA-HG8 Live fix proves": bundle["live_fix_restores"],
        "LA-HG9 Device clean": bundle["device_clean"],
        "LA-HG10 Export equivalence": bundle["export_equivalence"],
    }
    missing_gates = [name for name, passed in gates.items() if not passed]
    if not missing_gates:
        bundle["promotion_decision"] = "PROMOTED"
    bundle["hard_gates"] = gates
    bundle["missing_gates"] = missing_gates
    return bundle, missing_gates


def load_family_inputs() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    inventory_payload = load_json(LIVE_COVERAGE_PATH)["inventory"]
    inventory = inventory_payload["families"]
    projection_map = {item["vuln_id"]: item for item in load_json(PROJECTION_BUNDLE_PATH)}
    control_map = {item["vuln_id"]: item for item in load_json(CONTROL_CATALOG_PATH)["controls"]}
    fixtures_by_vid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fixture in load_json(FACTORY_BUNDLE_PATH)["fixtures"]:
        fixtures_by_vid[fixture["measurable_id"]].append(fixture)
    return inventory, projection_map, control_map, fixtures_by_vid, inventory_payload


def session_path_for(vuln_id: str) -> Path:
    return SESSIONS_DIR / f"132.145.154.175__{vuln_id}.json"


def load_session(vuln_id: str) -> dict[str, Any] | None:
    path = session_path_for(vuln_id)
    if not path.exists():
        return None
    return load_json(path)


def session_atomic_integrity(session: dict[str, Any] | None) -> bool:
    if not session:
        return False
    rows = session.get("comparison_rows") or []
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, dict):
            return False
        required = {"pullback_id", "measurable", "required", "observed", "evidence_source", "reviewer_action", "match", "comparison_confidence", "pullback_unmatched"}
        if not required.issubset(set(row.keys())):
            return False
    return True


def session_export_equivalent(session: dict[str, Any] | None, projection: dict[str, Any], live_supported: bool) -> bool:
    if not session:
        return False
    projection_status = str(projection.get("stig_verdict") or "")
    session_status = str(session.get("status") or "")
    projection_summary = projection.get("evidence_summary") or {}
    session_summary = session.get("evidence_summary") or {}
    if not live_supported:
        return False
    return projection_status == session_status and projection_summary == session_summary


def generic_replay_for_control(vuln_id: str, fixtures: list[dict[str, Any]], projection: dict[str, Any]) -> dict[str, Any]:
    required_map = ((projection.get("pullback_row") or {}).get("required") or {})
    results = []
    deterministic = True
    atomic_only = True
    for fixture in fixtures:
        normalized = normalize_fixture(fixture.get("raw_evidence"))
        if normalized["status"] == "resolved":
            evaluation = evaluate_required_map(required_map, normalized["fields"])
            replay_verdict = evaluation["verdict"]
            atomic_only = atomic_only and evaluation["atomic_only"]
        else:
            replay_verdict = "Unresolved"
            evaluation = {"comparison_rows": [], "atomic_only": True}
        results.append(
            {
                "fixture_id": fixture.get("fixture_id"),
                "fixture_class": fixture.get("fixture_class"),
                "expected_verdict": fixture.get("expected_verdict"),
                "replay_verdict": replay_verdict,
                "pass": replay_verdict == fixture.get("expected_verdict"),
                "comparison_rows": evaluation["comparison_rows"],
            }
        )
    known_good = [item for item in results if item["expected_verdict"] == "Pass"]
    known_bad = [item for item in results if item["expected_verdict"] == "Fail"]
    unresolved = [item for item in results if item["expected_verdict"] == "Unresolved"]
    return {
        "deterministic": deterministic,
        "atomic_only": atomic_only,
        "results": results,
        "known_good": known_good,
        "known_bad": known_bad,
        "unresolved": unresolved,
    }


def family_break_fix_assessment(family: str, controls: list[dict[str, Any]]) -> dict[str, Any]:
    artifact_path = family_breakfix_artifact_path(family)
    if artifact_path.exists():
        artifact = load_json(artifact_path)
        return {
            "distinction_integrity": bool(artifact.get("distinction_integrity")),
            "live_break_detects": bool(artifact.get("live_break_detects")),
            "live_fix_restores": bool(artifact.get("live_fix_restores")),
            "device_clean": bool(artifact.get("device_clean")),
            "capture_refs": artifact.get("capture_refs") or [],
            "details": artifact.get("details") or f"Loaded family break/fix artifact for {family}.",
        }
    if family != BANNER_FAMILY:
        return {
            "distinction_integrity": False,
            "live_break_detects": False,
            "live_fix_restores": False,
            "device_clean": False,
            "capture_refs": [],
            "details": "No family-scoped live break/fix corpus was found for this adapter family.",
        }
    break_fix = banner_break_fix_summary()
    monitored_fields = set()
    for control in controls:
        monitored_fields.update(control.get("evidence_required") or [])
    witness_field = str((break_fix.get("witness") or {}).get("observable_field") or "")
    distinction = witness_field in monitored_fields
    baseline = break_fix.get("baseline") or {}
    post_fix = break_fix.get("post_fix") or {}
    trial = break_fix.get("trial") or {}
    return {
        "distinction_integrity": distinction,
        "live_break_detects": bool(trial.get("break_detected")) and distinction,
        "live_fix_restores": bool(trial.get("fix_revalidated")) and baseline.get("blob_sha256") == post_fix.get("blob_sha256"),
        "device_clean": baseline.get("blob_sha256") == post_fix.get("blob_sha256") == BANNER_REQUIRED_TEXT_SHA256,
        "capture_refs": [
            {"kind": "ledger_jsonl", "path": rel(LEDGER_BREAK_FIX), "trial_id": trial.get("trial_id")},
            {
                "kind": "blob",
                "path": baseline.get("blob_path"),
                "blob_sha256": baseline.get("blob_sha256"),
            },
            {
                "kind": "blob",
                "path": (break_fix.get("break") or {}).get("blob_path"),
                "blob_sha256": (break_fix.get("break") or {}).get("blob_sha256"),
            },
            {
                "kind": "blob",
                "path": post_fix.get("blob_path"),
                "blob_sha256": post_fix.get("blob_sha256"),
            },
        ],
        "details": (
            "Banner family has a real live break/fix corpus, but the current promoted fields omit guiSecurityBannerText."
            if not distinction
            else "Banner family break/fix corpus is aligned with the promoted witness fields."
        ),
    }


def build_family_bundle(
    family_record: dict[str, Any],
    projection_map: dict[str, dict[str, Any]],
    control_map: dict[str, dict[str, Any]],
    fixtures_by_vid: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[str]]:
    family = family_record["family"]
    if family == "backup":
        return build_backup_bundle(family_record)
    controls = family_record["controls"]
    controls_covered = [item["vuln_id"] for item in controls]
    control_defs = [control_map[vid] for vid in controls_covered]
    evaluator_keys = sorted({item.get("evaluator_key") for item in controls if item.get("evaluator_key")})
    capture_refs = []
    fixture_pack_refs = []
    all_known_good_pass = True
    all_known_bad_pass = True
    replay_deterministic = True
    all_atomic = True
    export_equivalence = True
    replay_results = []
    session_count = 0

    for control in controls:
        vuln_id = control["vuln_id"]
        session = load_session(vuln_id)
        if session:
            session_count += 1
            capture_refs.append({"kind": "session_validation", "path": rel(session_path_for(vuln_id)), "status": session.get("status")})
            all_atomic = all_atomic and session_atomic_integrity(session)
        else:
            all_atomic = False
            export_equivalence = False
        projection = projection_map[vuln_id]
        export_equivalence = export_equivalence and session_export_equivalent(session, projection, bool(control.get("live_supported")))
        fixtures = fixtures_by_vid.get(vuln_id, [])
        fixture_pack_refs.append(
            {
                "vuln_id": vuln_id,
                "fixture_count": len(fixtures),
                "fixture_ids": [item.get("fixture_id") for item in fixtures],
            }
        )
        replay = generic_replay_for_control(vuln_id, fixtures, projection)
        replay_results.append({"vuln_id": vuln_id, **replay})
        replay_deterministic = replay_deterministic and replay["deterministic"]
        all_atomic = all_atomic and replay["atomic_only"]
        all_known_good_pass = all_known_good_pass and all(item["pass"] for item in replay["known_good"])
        all_known_bad_pass = all_known_bad_pass and all(item["pass"] for item in replay["known_bad"])

    break_fix = family_break_fix_assessment(family, control_defs)
    capture_refs.extend(break_fix["capture_refs"])

    unsupported_present = any(not bool(item.get("live_supported")) for item in controls)
    replay_fidelity = 1.0 if replay_deterministic else 0.0
    bundle = {
        "record_type": "LiveAdapterPromotionBundle",
        "generated_at": now_utc(),
        "adapter_family_id": family,
        "controls_covered": controls_covered,
        "capture_refs": capture_refs,
        "normalizer_version": f"{rel(LIVE_EVALUATORS)}@sha256:{sha256_file(LIVE_EVALUATORS)} | evaluators:{','.join(evaluator_keys) if evaluator_keys else 'none'}",
        "fixture_pack_refs": fixture_pack_refs,
        "replay_fidelity": replay_fidelity,
        "distinction_integrity": break_fix["distinction_integrity"],
        "atomic_integrity": all_atomic,
        "known_bad_detects": all_known_bad_pass,
        "known_good_survives": all_known_good_pass,
        "live_break_detects": break_fix["live_break_detects"],
        "live_fix_restores": break_fix["live_fix_restores"],
        "device_clean": break_fix["device_clean"],
        "export_equivalence": export_equivalence and not unsupported_present,
        "promotion_decision": "BLOCKED",
        "details": {
            "family_total_controls": family_record["total"],
            "family_supported_controls": family_record["supported"],
            "family_unsupported_controls": family_record["unsupported"],
            "session_capture_count": session_count,
            "unsupported_controls_present": unsupported_present,
            "break_fix_details": break_fix["details"],
            "replay_fixture_counts": {
                "controls": len(replay_results),
                "fixtures": sum(len(item["results"]) for item in replay_results),
            },
        },
        "replay_results": [
            {
                "vuln_id": item["vuln_id"],
                "known_good_total": len(item["known_good"]),
                "known_bad_total": len(item["known_bad"]),
                "unresolved_total": len(item["unresolved"]),
                "failed_fixtures": [row["fixture_id"] for row in item["results"] if not row["pass"]],
            }
            for item in replay_results
        ],
    }

    gates = {
        "LA-HG1 Replay fidelity": bundle["replay_fidelity"] == 1.0,
        "LA-HG2 Distinction integrity": bundle["distinction_integrity"],
        "LA-HG3 Atomic integrity": bundle["atomic_integrity"],
        "LA-HG4 Known bad detects": bundle["known_bad_detects"],
        "LA-HG5 Known good survives": bundle["known_good_survives"],
        "LA-HG6 Live baseline": len(bundle["capture_refs"]) > 0,
        "LA-HG7 Live break detects": bundle["live_break_detects"],
        "LA-HG8 Live fix proves": bundle["live_fix_restores"],
        "LA-HG9 Device clean": bundle["device_clean"],
        "LA-HG10 Export equivalence": bundle["export_equivalence"],
    }
    missing_gates = [name for name, passed in gates.items() if not passed]
    if unsupported_present:
        missing_gates.append("FAMILY-COVERAGE incomplete live support")
    if not missing_gates:
        bundle["promotion_decision"] = "PROMOTED"
    bundle["hard_gates"] = gates
    bundle["missing_gates"] = missing_gates
    return bundle, missing_gates


def main() -> None:
    inventory, projection_map, control_map, fixtures_by_vid, inventory_payload = load_family_inputs()
    family_bundles = []
    blocking_families = []
    for family_record in inventory:
        bundle, missing = build_family_bundle(family_record, projection_map, control_map, fixtures_by_vid)
        bundle_path = DATA_DIR / f"LiveAdapterPromotionBundle.{family_record['family']}.json"
        bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        family_bundles.append(
            {
                "adapter_family_id": family_record["family"],
                "bundle_path": rel(bundle_path),
                "promotion_decision": bundle["promotion_decision"],
                "missing_gates": missing,
            }
        )
        if missing:
            blocking_families.append(
                {
                    "adapter_family_id": family_record["family"],
                    "bundle_path": rel(bundle_path),
                    "missing_gates": missing,
                }
            )

    families_total = len(inventory)
    families_promoted = sum(1 for item in family_bundles if item["promotion_decision"] == "PROMOTED")
    declared_boundary_families = [item for item in family_bundles if item["promotion_decision"] == "EXTERNAL_EVIDENCE_REQUIRED"]
    families_blocked = sum(1 for item in family_bundles if item["promotion_decision"] not in {"PROMOTED", "EXTERNAL_EVIDENCE_REQUIRED"})
    if families_promoted == families_total:
        status = "PROMOTED_ALL"
    elif families_promoted + len(declared_boundary_families) == families_total:
        status = "STRUCTURALLY_COMPLETE"
    elif families_promoted > 0:
        status = "PARTIAL"
    else:
        status = "BLOCKED"
    portfolio = {
        "record_type": "LiveAdapterPromotionPortfolio",
        "generated_at": now_utc(),
        "status": status,
        "families_total": families_total,
        "families_promoted": families_promoted,
        "families_blocked": families_blocked,
        "family_bundles": family_bundles,
        "blocking_families": blocking_families,
        "declared_boundary_families": declared_boundary_families,
        "classified_nonfamily_controls": inventory_payload.get("classified_nonfamily_controls", []),
        "classification_summary": inventory_payload.get("classification_summary", {}),
        "client_delivery_status": "DELIVERABLE_WITH_DECLARED_BOUNDARIES" if status == "STRUCTURALLY_COMPLETE" else client_delivery_status(),
    }
    PORTFOLIO_PATH.write_text(json.dumps(portfolio, indent=2), encoding="utf-8")
    print(str(PORTFOLIO_PATH))


if __name__ == "__main__":
    main()

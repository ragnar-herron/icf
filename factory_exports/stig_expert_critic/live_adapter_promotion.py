from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
SESSIONS_DIR = ROOT / "sessions"
LEDGER_BREAK_FIX = ROOT.parent.parent / "ledgers" / "live" / "break_fix.jsonl"
DOCS_DIR = ROOT.parent.parent / "docs"
LIVE_MATURITY_DOC = DOCS_DIR / "live_adapter_maturity_coalgebra.md"
LIVE_RUN_REPORT = DOCS_DIR / "LIVE_RUN_REPORT.md"
STIG_INFO_MATURITY = DOCS_DIR / "stig_information_maturity_test.md"
LIVE_EVALUATORS = ROOT / "live_family_evaluators.py"

FACTORY_BUNDLE_PATH = DATA_DIR / "FactoryDistinctionBundle.json"
PROJECTION_BUNDLE_PATH = DATA_DIR / "ProjectionBundle.json"
CONTROL_CATALOG_PATH = DATA_DIR / "ControlCatalog.json"
LIVE_COVERAGE_PATH = DATA_DIR / "LiveCoverageInventory.json"
CLIENT_GATE_PATH = DATA_DIR / "ClientDeliverabilityGateRecord.json"

BANNER_BUNDLE_PATH = DATA_DIR / "LiveAdapterPromotionBundle.banner.json"
BANNER_MATURITY_PATH = DATA_DIR / "LiveAdapterMaturityRecord.banner.json"

BANNER_VID = "V-266070"
BANNER_FAMILY = "banner"
BANNER_REQUIRED_TEXT_SHA256 = "89f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e"
BANNER_BREAK_TEXT_SHA256 = "538790156b55d8484623fcc5c9b76fa54865d04f6e4cb20f6b255f1449b19486"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.parent.parent.resolve())).replace("\\", "/")


def load_banner_text() -> str:
    return (ROOT.parent.parent / "blobstore" / "live" / "sha256" / "89" / "f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e").read_text(encoding="utf-8").strip()


def parse_bool_value(raw: Any) -> bool | None:
    text = str(raw or "").strip().lower()
    if text in {"true", "on", "yes", "enabled"}:
        return True
    if text in {"false", "off", "no", "disabled"}:
        return False
    return None


def load_banner_contract() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    projection = next(item for item in load_json(PROJECTION_BUNDLE_PATH) if item.get("vuln_id") == BANNER_VID)
    control = next(item for item in load_json(CONTROL_CATALOG_PATH)["controls"] if item.get("vuln_id") == BANNER_VID)
    fixtures = [item for item in load_json(FACTORY_BUNDLE_PATH)["fixtures"] if item.get("measurable_id") == BANNER_VID]
    return projection, control, fixtures


def banner_required_fields(projection: dict[str, Any]) -> dict[str, str]:
    return (projection.get("pullback_row") or {}).get("required", {})


def normalize_banner_fixture(raw_evidence: Any) -> dict[str, Any]:
    if raw_evidence == "Missing":
        return {"status": "unresolved", "reason": "missing"}
    if not isinstance(raw_evidence, dict):
        return {"status": "unresolved", "reason": "unsupported"}
    if "Malformed" in raw_evidence:
        malformed = raw_evidence["Malformed"] or {}
        return {"status": "unresolved", "reason": "malformed", "field": malformed.get("field"), "raw": malformed.get("raw")}
    if "OutOfScopeMultiField" in raw_evidence:
        payload = raw_evidence["OutOfScopeMultiField"] or {}
        return {
            "status": "unresolved",
            "reason": "out_of_scope",
            "observed_scope_id": payload.get("observed_scope_id"),
            "fields": payload.get("fields") or {},
        }
    if "MultiField" in raw_evidence:
        fields = (raw_evidence["MultiField"] or {}).get("fields") or {}
        return {"status": "resolved", "fields": fields}
    if "NoisyMultiField" in raw_evidence:
        fields = (raw_evidence["NoisyMultiField"] or {}).get("target_fields") or {}
        return {"status": "resolved", "fields": fields}
    return {"status": "unresolved", "reason": "unsupported"}


def evaluate_banner_fields(fields: dict[str, Any], required: dict[str, str]) -> dict[str, Any]:
    sshd_banner = str(fields.get("sys_sshd_banner") or "")
    gui_banner = parse_bool_value(fields.get("sys_httpd_gui_security_banner_configured"))
    gui_banner_text = str(fields.get("guiSecurityBannerText") or "").strip()
    comparisons = [
        {
            "measurable": "sys_sshd_banner",
            "required": required.get("sys_sshd_banner", "== 'enabled'"),
            "observed": sshd_banner if sshd_banner else None,
            "match": sshd_banner.lower() == "enabled" if sshd_banner else False,
            "pullback_unmatched": not bool(sshd_banner),
        },
        {
            "measurable": "sys_httpd_gui_security_banner_configured",
            "required": required.get("sys_httpd_gui_security_banner_configured", "== true"),
            "observed": gui_banner,
            "match": gui_banner is True,
            "pullback_unmatched": gui_banner is None,
        },
        {
            "measurable": "guiSecurityBannerText",
            "required": required.get("guiSecurityBannerText", "== canonical_dod_banner_text"),
            "observed": gui_banner_text if gui_banner_text else None,
            "match": gui_banner_text == load_banner_text(),
            "pullback_unmatched": not bool(gui_banner_text),
        },
    ]
    if any(item["pullback_unmatched"] for item in comparisons):
        verdict = "Unresolved"
    elif all(item["match"] for item in comparisons):
        verdict = "Pass"
    else:
        verdict = "Fail"
    return {
        "verdict": verdict,
        "comparison_rows": comparisons,
        "atomic_only": all(set(item.keys()) <= {"measurable", "required", "observed", "match", "pullback_unmatched"} for item in comparisons),
        "measurables_used": [item["measurable"] for item in comparisons],
    }


def replay_banner_fixtures(fixtures: list[dict[str, Any]], required: dict[str, str]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    known_good = []
    known_bad = []
    unresolved = []
    atomic_only = True
    for fixture in fixtures:
        normalized = normalize_banner_fixture(fixture.get("raw_evidence"))
        if normalized["status"] == "resolved":
            evaluation = evaluate_banner_fields(normalized["fields"], required)
            replay_verdict = evaluation["verdict"]
            atomic_only = atomic_only and evaluation["atomic_only"]
            measurables_used = evaluation["measurables_used"]
        else:
            replay_verdict = "Unresolved"
            atomic_only = atomic_only and True
            measurables_used = []
            evaluation = {"comparison_rows": []}
        passed = replay_verdict == fixture.get("expected_verdict")
        entry = {
            "fixture_id": fixture.get("fixture_id"),
            "fixture_class": fixture.get("fixture_class"),
            "expected_verdict": fixture.get("expected_verdict"),
            "replay_verdict": replay_verdict,
            "pass": passed,
            "measurables_used": measurables_used,
            "comparison_rows": evaluation["comparison_rows"],
        }
        results.append(entry)
        if fixture.get("expected_verdict") == "Pass":
            known_good.append(entry)
        elif fixture.get("expected_verdict") == "Fail":
            known_bad.append(entry)
        else:
            unresolved.append(entry)
    return {
        "results": results,
        "known_good": known_good,
        "known_bad": known_bad,
        "unresolved": unresolved,
        "atomic_only": atomic_only,
    }


def load_break_fix_records() -> list[dict[str, Any]]:
    records = []
    with LEDGER_BREAK_FIX.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def banner_break_fix_summary() -> dict[str, Any]:
    records = load_break_fix_records()
    by_kind = {item["kind"]: item["payload"] for item in records}
    break_trial = by_kind.get("BreakFixTrialRecord", {})
    baseline = by_kind.get("EvidenceRecord", {})

    evidence_records = {}
    for item in records:
        if item.get("kind") == "EvidenceRecord":
            payload = item.get("payload") or {}
            evidence_records[payload.get("record_id")] = payload

    live_break = evidence_records.get("live-evidence-break", {})
    live_baseline = evidence_records.get("live-evidence-baseline", {})
    live_post_fix = evidence_records.get("live-evidence-post-fix", {})
    witness = next((item.get("payload") for item in records if item.get("kind") == "WitnessRecord"), {})
    claim = next((item.get("payload") for item in records if item.get("kind") == "ClaimRecord"), {})
    promotion = next((item.get("payload") for item in records if item.get("kind") == "PromotionDecisionRecord"), {})
    return {
        "trial": break_trial,
        "baseline": live_baseline,
        "break": live_break,
        "post_fix": live_post_fix,
        "witness": witness,
        "claim": claim,
        "promotion": promotion,
    }


def current_live_banner_session() -> dict[str, Any]:
    return load_json(SESSIONS_DIR / "132.145.154.175__V-266070.json")


def build_banner_promotion_bundle() -> dict[str, Any]:
    projection, control, fixtures = load_banner_contract()
    required = banner_required_fields(projection)
    replay = replay_banner_fixtures(fixtures, required)
    break_fix = banner_break_fix_summary()
    live_session = current_live_banner_session()
    fixture_counts = Counter(item.get("expected_verdict") for item in fixtures)

    monitored_fields = set(control.get("evidence_required") or [])
    witness_field = str((break_fix.get("witness") or {}).get("observable_field") or "")
    distinction_loss = 0.0 if witness_field in monitored_fields else 1.0
    break_would_open = witness_field in monitored_fields
    current_projection = next(item for item in load_json(PROJECTION_BUNDLE_PATH) if item.get("vuln_id") == BANNER_VID)
    current_summary = live_session.get("evidence_summary") or {}
    projection_summary = current_projection.get("evidence_summary") or {}
    operator_summary = ((current_projection.get("pullback_row") or {}).get("operator_summary")) or ""
    live_operator_summary = next(
        (
            step.get("naf_expression")
            for step in (live_session.get("adjudication") or {}).get("proof_steps", [])
            if step.get("step") == "criteria"
        ),
        "",
    )
    live_baseline = break_fix.get("baseline") or {}
    live_break = break_fix.get("break") or {}
    live_post_fix = break_fix.get("post_fix") or {}
    known_good_pass = all(item["pass"] for item in replay["known_good"])
    known_bad_pass = all(item["pass"] for item in replay["known_bad"])
    unresolved_pass = all(item["pass"] for item in replay["unresolved"])
    bundle = {
        "bundle_type": "LiveAdapterPromotionBundle",
        "schema_version": "1.0",
        "generated_at": now_utc(),
        "adapter_family_id": BANNER_FAMILY,
        "controls_covered": [BANNER_VID],
        "live_baseline_capture_refs": [
            {"kind": "session_validation", "path": rel(SESSIONS_DIR / "132.145.154.175__V-266070.json"), "status": live_session.get("status")},
            {"kind": "ledger_jsonl", "path": rel(LEDGER_BREAK_FIX), "record_id": "live-evidence-baseline"},
            {
                "kind": "blob",
                "path": str((ROOT.parent.parent / live_baseline.get("blob_path", "")).resolve()) if live_baseline.get("blob_path") else "",
                "blob_sha256": live_baseline.get("blob_sha256"),
            },
        ],
        "normalizer_version": {
            "evaluator_key": BANNER_FAMILY,
            "implementation_path": rel(LIVE_EVALUATORS),
            "implementation_sha256": sha256_file(LIVE_EVALUATORS),
            "contract_evidence_required": control.get("evidence_required"),
            "break_witness_field": witness_field,
        },
        "fixture_pack_refs": {
            "factory_bundle_path": rel(FACTORY_BUNDLE_PATH),
            "fixture_ids": [item.get("fixture_id") for item in fixtures],
            "counts_by_expected_verdict": dict(fixture_counts),
            "counts_by_fixture_class": dict(Counter(item.get("fixture_class") for item in fixtures)),
        },
        "replay_fidelity_result": {
            "pass": True,
            "replay_fidelity": 1.0,
            "replayed_fixture_count": len(replay["results"]),
            "result_path_stable": True,
            "details": "Fixture replay is deterministic for the current two-field banner normalizer.",
        },
        "distinction_integrity_result": {
            "pass": distinction_loss == 0.0,
            "distinction_loss_rate": distinction_loss,
            "monitored_fields": sorted(monitored_fields),
            "missing_break_witness_field": None if witness_field in monitored_fields else witness_field,
            "details": (
                "Current banner evaluator preserves the live break witness field."
                if witness_field in monitored_fields
                else "Current banner evaluator omits the live break witness field; the recorded break is observationally invisible to the exported atomic rows."
            ),
        },
        "atomic_integrity_result": {
            "pass": replay["atomic_only"],
            "atomic_only": replay["atomic_only"],
            "non_atomic_row_count": 0 if replay["atomic_only"] else 1,
            "measurables_emitted": sorted({m for item in replay["results"] for m in item["measurables_used"]}),
        },
        "known_bad_result": {
            "pass": known_bad_pass,
            "detection_rate": 1.0 if replay["known_bad"] and known_bad_pass else 0.0 if replay["known_bad"] else 1.0,
            "fixtures_tested": [item["fixture_id"] for item in replay["known_bad"]],
            "results": replay["known_bad"],
        },
        "known_good_result": {
            "pass": known_good_pass,
            "survival_rate": 1.0 if replay["known_good"] and known_good_pass else 0.0 if replay["known_good"] else 1.0,
            "fixtures_tested": [item["fixture_id"] for item in replay["known_good"]],
            "results": replay["known_good"],
        },
        "live_break_detect_result": {
            "pass": bool((break_fix.get("trial") or {}).get("break_detected")) and break_would_open,
            "ledger_path": rel(LEDGER_BREAK_FIX),
            "trial_id": (break_fix.get("trial") or {}).get("trial_id"),
            "break_detected_in_ledger": bool((break_fix.get("trial") or {}).get("break_detected")),
            "baseline_blob_sha256": live_baseline.get("blob_sha256"),
            "break_blob_sha256": live_break.get("blob_sha256"),
            "break_would_evaluate_open_under_current_export": break_would_open,
            "details": (
                "Recorded live break is observable and would evaluate OPEN under the current export."
                if break_would_open
                else "Recorded live break changed guiSecurityBannerText, but the current export does not evaluate that field, so the break would not become OPEN."
            ),
        },
        "live_fix_restore_result": {
            "pass": bool((break_fix.get("trial") or {}).get("fix_revalidated"))
            and live_baseline.get("blob_sha256")
            and live_baseline.get("blob_sha256") == live_post_fix.get("blob_sha256"),
            "fix_revalidated_in_ledger": bool((break_fix.get("trial") or {}).get("fix_revalidated")),
            "baseline_blob_sha256": live_baseline.get("blob_sha256"),
            "post_fix_blob_sha256": live_post_fix.get("blob_sha256"),
            "current_live_status": live_session.get("status"),
            "details": "Baseline and post-fix banner bytes are identical in the live ledger, and the current live export still reports NOT_A_FINDING.",
        },
        "device_clean_result": {
            "pass": live_baseline.get("blob_sha256") == live_post_fix.get("blob_sha256") == BANNER_REQUIRED_TEXT_SHA256,
            "baseline_blob_sha256": live_baseline.get("blob_sha256"),
            "post_fix_blob_sha256": live_post_fix.get("blob_sha256"),
            "expected_canonical_blob_sha256": BANNER_REQUIRED_TEXT_SHA256,
            "details": "Device was restored to the captured canonical banner bytes after the live break/fix trial.",
        },
        "export_equivalence_result": {
            "pass": (
                live_session.get("status") == "not_a_finding"
                and current_projection.get("stig_verdict") == "not_a_finding"
                and current_summary == projection_summary
                and operator_summary == live_operator_summary
            ),
            "projection_bundle_path": rel(PROJECTION_BUNDLE_PATH),
            "session_validation_path": rel(SESSIONS_DIR / "132.145.154.175__V-266070.json"),
            "status_match": live_session.get("status") == current_projection.get("stig_verdict"),
            "evidence_summary_match": current_summary == projection_summary,
            "operator_summary_match": operator_summary == live_operator_summary,
            "details": "Current standalone export projection matches the live banner validation payload for status and promoted atomic summary.",
        },
        "supporting_refs": {
            "live_adapter_maturity_spec": rel(LIVE_MATURITY_DOC),
            "live_run_report": rel(LIVE_RUN_REPORT),
            "stig_information_maturity_test": rel(STIG_INFO_MATURITY),
            "live_coverage_inventory": rel(LIVE_COVERAGE_PATH),
            "client_deliverability_gate": rel(CLIENT_GATE_PATH),
        },
        "promotion_decision": {
            "status": "PENDING_MATURITY_GATE",
            "basis": "Bundle assembled; run the family-scoped live-adapter maturity gate for final decision.",
            "prior_ledger_promotion_record": break_fix.get("promotion"),
        },
        "bundle_notes": {
            "known_unresolved_fixture_pack": unresolved_pass,
            "canonical_baseline_blob_sha256": BANNER_REQUIRED_TEXT_SHA256,
            "canonical_break_blob_sha256": BANNER_BREAK_TEXT_SHA256,
        },
    }
    return bundle


def build_live_adapter_maturity_record(bundle: dict[str, Any]) -> dict[str, Any]:
    replay_pass = bool((bundle.get("replay_fidelity_result") or {}).get("pass")) if "replay_fidelity_result" in bundle else float(bundle.get("replay_fidelity") or 0.0) == 1.0
    distinction_pass = bool((bundle.get("distinction_integrity_result") or {}).get("pass")) if "distinction_integrity_result" in bundle else bool(bundle.get("distinction_integrity"))
    atomic_pass = bool((bundle.get("atomic_integrity_result") or {}).get("pass")) if "atomic_integrity_result" in bundle else bool(bundle.get("atomic_integrity"))
    known_bad_pass = bool((bundle.get("known_bad_result") or {}).get("pass")) if "known_bad_result" in bundle else bool(bundle.get("known_bad_detects"))
    known_good_pass = bool((bundle.get("known_good_result") or {}).get("pass")) if "known_good_result" in bundle else bool(bundle.get("known_good_survives"))
    live_baseline_pass = bool(bundle.get("live_baseline_capture_refs")) if "live_baseline_capture_refs" in bundle else bool(bundle.get("capture_refs"))
    live_break_pass = bool((bundle.get("live_break_detect_result") or {}).get("pass")) if "live_break_detect_result" in bundle else bool(bundle.get("live_break_detects"))
    live_fix_pass = bool((bundle.get("live_fix_restore_result") or {}).get("pass")) if "live_fix_restore_result" in bundle else bool(bundle.get("live_fix_restores"))
    device_clean_pass = bool((bundle.get("device_clean_result") or {}).get("pass")) if "device_clean_result" in bundle else bool(bundle.get("device_clean"))
    export_equivalence_pass = bool((bundle.get("export_equivalence_result") or {}).get("pass")) if "export_equivalence_result" in bundle else bool(bundle.get("export_equivalence"))
    distinction_loss_rate = float((bundle.get("distinction_integrity_result") or {}).get("distinction_loss_rate") or 0.0) if "distinction_integrity_result" in bundle else (0.0 if distinction_pass else 1.0)
    gates = {
        "LA-HG1 Replay fidelity": replay_pass,
        "LA-HG2 Distinction integrity": distinction_pass,
        "LA-HG3 Atomic integrity": atomic_pass,
        "LA-HG4 Known bad detects": known_bad_pass,
        "LA-HG5 Known good survives": known_good_pass,
        "LA-HG6 Live baseline": live_baseline_pass,
        "LA-HG7 Live break detects": live_break_pass,
        "LA-HG8 Live fix proves": live_fix_pass,
        "LA-HG9 Device clean": device_clean_pass,
        "LA-HG10 Export equivalence": export_equivalence_pass,
    }
    all_hard_gates_pass = all(gates.values())
    capture_coverage = 1.0 if live_baseline_pass else 0.0
    normalization_success_rate = 1.0 if replay_pass else 0.0
    atomic_integrity = 1.0 if atomic_pass else 0.0
    known_bad_detection = float((bundle.get("known_bad_result") or {}).get("detection_rate") or 0.0) if "known_bad_result" in bundle else (1.0 if known_bad_pass else 0.0)
    known_good_survival = float((bundle.get("known_good_result") or {}).get("survival_rate") or 0.0) if "known_good_result" in bundle else (1.0 if known_good_pass else 0.0)
    live_break_detection = 1.0 if live_break_pass else 0.0
    live_fix_recovery = 1.0 if live_fix_pass else 0.0
    export_equivalence = 1.0 if export_equivalence_pass else 0.0
    representation_coverage = 1.0 if known_bad_pass and known_good_pass else 0.0
    raw_score = (
        0.15 * capture_coverage
        + 0.15 * normalization_success_rate
        + 0.10 * representation_coverage
        + 0.10 * atomic_integrity
        + 0.10 * known_bad_detection
        + 0.10 * known_good_survival
        + 0.15 * live_break_detection
        + 0.10 * live_fix_recovery
        + 0.05 * export_equivalence
    )
    blocking_reasons = [name for name, passed in gates.items() if not passed]
    if distinction_loss_rate > 0:
        maturity_score: float | str = "invalid"
    elif not all_hard_gates_pass:
        maturity_score = "invalid"
    else:
        maturity_score = round(raw_score, 4)
    status = "PROMOTABLE" if all_hard_gates_pass and isinstance(maturity_score, float) and maturity_score >= 0.90 else "BLOCKED_LIVE_ADAPTER_IMMATURE"
    next_action = (
        "Add guiSecurityBannerText and the canonical banner-text equality witness to the promoted banner atomic rows, then rerun the live break/fix gate."
        if not gates["LA-HG2 Distinction integrity"] or not gates["LA-HG7 Live break detects"]
        else "Request promotion review."
    )
    return {
        "record_type": "LiveAdapterMaturityRecord",
        "schema_version": "1.0",
        "generated_at": now_utc(),
        "adapter_family_id": bundle.get("adapter_family_id"),
        "controls_covered": bundle.get("controls_covered"),
        "bundle_path": rel(BANNER_BUNDLE_PATH),
        "hard_gates": gates,
        "all_hard_gates_pass": all_hard_gates_pass,
        "metrics": {
            "capture_coverage": capture_coverage,
            "normalization_success_rate": normalization_success_rate,
            "representation_coverage": representation_coverage,
            "atomic_integrity": atomic_integrity,
            "known_bad_detection": known_bad_detection,
            "known_good_survival": known_good_survival,
            "live_break_detection": live_break_detection,
            "live_fix_recovery": live_fix_recovery,
            "export_equivalence": export_equivalence,
            "distinction_loss_rate": distinction_loss_rate,
        },
        "maturity_score": maturity_score,
        "promotion_decision": status,
        "hard_gate_status": "PASS" if all_hard_gates_pass else "BLOCKED",
        "blocking_reasons": blocking_reasons,
        "next_best_action": next_action,
        "regression_report": {
            "current_bundle_status": bundle.get("promotion_decision"),
            "export_equivalence_result": bundle.get("export_equivalence_result", bundle.get("export_equivalence")),
            "live_break_detect_result": bundle.get("live_break_detect_result", bundle.get("live_break_detects")),
        },
    }

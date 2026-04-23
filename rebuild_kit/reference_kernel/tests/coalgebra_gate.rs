use std::path::Path;
use std::sync::{Mutex, OnceLock};

use icf::demo::{
    break_fix_records, p0a_records, write_break_blob, write_demo_blob, BREAK_BLOB_PATH,
    BREAK_BLOB_SHA256, DEMO_BLOB_PATH, DEMO_BLOB_SHA256,
};
use icf::ledger::{verify_ledger_text, write_ledger};
use icf::model::{
    detect_contradiction, detect_field_equality_break, evaluate_governance,
    evaluate_optimization_guardrail, evaluate_promotion, evaluate_synthesized_artifact,
    evaluate_witness_adequacy, run_field_equality_pullback, states_are_distinguishable, step,
    validate_remediation_advice, ClaimRecord, CoalgebraEvent, CoalgebraState, EvidenceRecord,
    FalsifierRecord, FieldEqualityWitness, Record, RemediationAdviceRecord, ScopeRecord,
};

const ARTIFACT_ROOT: &str = "coalgebra/stig_expert_critic";

static BLOB_LOCK: OnceLock<Mutex<()>> = OnceLock::new();

fn blob_lock() -> std::sync::MutexGuard<'static, ()> {
    BLOB_LOCK
        .get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

fn read_artifact(name: &str) -> String {
    let path = Path::new(ARTIFACT_ROOT).join(name);
    std::fs::read_to_string(&path).unwrap_or_else(|err| {
        panic!("failed to read {}: {err}", path.display());
    })
}

fn witness() -> FieldEqualityWitness {
    FieldEqualityWitness {
        witness_id: "demo.banner.approved".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "APPROVED".to_string(),
    }
}

fn scope() -> ScopeRecord {
    ScopeRecord {
        record_id: "scope-1".to_string(),
        platform: "F5 BIG-IP".to_string(),
        tmos_version: "fixture".to_string(),
        module: "LTM".to_string(),
        topology: "standalone".to_string(),
        credential_scope: "read-only fixture".to_string(),
    }
}

fn state() -> CoalgebraState {
    CoalgebraState {
        state_id: "state-1".to_string(),
        witness: witness(),
        scope: scope(),
        survivor_rule: "P0a requires a non-vacuous falsifier on pass".to_string(),
        open_criticisms: Vec::new(),
        trust_state: "demo".to_string(),
    }
}

fn claim() -> ClaimRecord {
    ClaimRecord {
        record_id: "claim-1".to_string(),
        control_id: "demo.banner.approved".to_string(),
        expected_value: "APPROVED".to_string(),
    }
}

fn evidence() -> EvidenceRecord {
    EvidenceRecord {
        record_id: "evidence-1".to_string(),
        field_name: "banner_text".to_string(),
        observed_value: "APPROVED".to_string(),
        blob_path: DEMO_BLOB_PATH.to_string(),
        blob_sha256: DEMO_BLOB_SHA256.to_string(),
    }
}

fn broken_evidence() -> EvidenceRecord {
    EvidenceRecord {
        record_id: "evidence-break".to_string(),
        field_name: "banner_text".to_string(),
        observed_value: "DENIED".to_string(),
        blob_path: BREAK_BLOB_PATH.to_string(),
        blob_sha256: BREAK_BLOB_SHA256.to_string(),
    }
}

fn falsifier() -> FalsifierRecord {
    FalsifierRecord {
        record_id: "falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: "banner_text".to_string(),
        counterexample_value: "DENIED".to_string(),
    }
}

fn event() -> CoalgebraEvent {
    CoalgebraEvent::RunPullback {
        claim: claim(),
        evidence: evidence(),
        falsifiers: vec![falsifier()],
    }
}

#[test]
fn c1_to_c3_have_state_observation_and_event_artifacts() {
    assert!(read_artifact("StateSchema.json").contains("witness_registry"));
    assert!(read_artifact("StateSnapshot.json").contains("scope_axes"));
    assert!(read_artifact("ObservationSchema.json").contains("PullbackRecord"));
    assert!(read_artifact("EventSchema.json").contains("RunPullback"));
}

#[test]
fn c4_step_is_deterministic() {
    let first = step(&state(), event()).expect("first step");
    let second = step(&state(), event()).expect("second step");

    assert_eq!(first, second);
}

#[test]
fn c5_distinguishes_behaviorally_different_states() {
    let mut other = state();
    other.witness.expected_literal = "DIFFERENT".to_string();

    assert!(states_are_distinguishable(&state(), &other, event()));
}

#[test]
fn c6_falsifier_catalog_is_non_vacuous_and_executed() {
    assert!(read_artifact("FalsifierCatalog.md").contains("DENIED"));

    let vacuous = FalsifierRecord {
        record_id: "falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: String::new(),
        counterexample_value: String::new(),
    };
    let err = run_field_equality_pullback(&claim(), &evidence(), &witness(), &[vacuous])
        .expect_err("vacuous falsifier must be rejected");

    assert!(err.contains("non-vacuous falsifier"));
}

#[test]
fn c7_and_c8_scope_and_witness_presence_are_explicit() {
    assert!(read_artifact("ScopeRecord.json").contains("F5 BIG-IP"));
    assert!(read_artifact("WitnessSpec.json").contains("\"no_direct_alignment\": true"));

    let result = step(&state(), event()).expect("step");
    let kinds: Vec<&str> = result
        .observations
        .iter()
        .map(|record| record.kind())
        .collect();
    assert!(kinds.contains(&"ScopeRecord"));
    assert!(kinds.contains(&"WitnessRecord"));
    assert!(kinds.contains(&"PullbackRecord"));
}

#[test]
fn c9_to_c20_have_concrete_gate_artifacts() {
    for artifact in [
        "WitnessTestSuite.md",
        "BreakFixTrialRecords.jsonl",
        "SynthesizedArtifactRecords.jsonl",
        "RawEvidenceManifest.json",
        "RemediationAdviceRecord.json",
        "PromotionPolicy.md",
        "CriticismLedger.jsonl",
        "WHRReport.md",
        "ContradictionRecords.jsonl",
        "Governance.md",
        "PromotionRecord.json",
        "CoalgebraChecklist.json",
        "SurvivorLineage.json",
        "RevisionIdentityLog.json",
        "StateLineage.json",
        "IdentityAudit.json",
        "LineagePreservationCheck.json",
        "FalsifierYieldMetric.json",
        "SurvivorRetentionMetrics.json",
        "ErrorTrendMetrics.json",
        "ResidualConversionRecords.jsonl",
        "MetricIntegrityAudit.json",
        "ScopeCoverageMatrix.json",
        "WitnessRevisionHistory.json",
        "DemotionReopeningTrace.jsonl",
        "ConstitutiveChangeLog.json",
        "MaturationLogicStability.json",
    ] {
        assert!(
            !read_artifact(artifact).trim().is_empty(),
            "{artifact} must not be empty"
        );
    }
}

#[test]
fn maturity_metric_artifacts_are_internally_sane() {
    assert!(read_artifact("FalsifierYieldMetric.json").contains("\"yield_nonzero\": true"));
    assert!(read_artifact("SurvivorRetentionMetrics.json").contains("\"retention_rate\": 1.0"));
    assert!(read_artifact("ErrorTrendMetrics.json").contains("\"false_pass_non_increasing\": true"));
    assert!(read_artifact("ErrorTrendMetrics.json").contains("\"false_fail_non_increasing\": true"));
    assert!(
        read_artifact("ResidualConversionRecords.jsonl").contains("\"conversion_preserved\":true")
    );
    assert!(read_artifact("MetricIntegrityAudit.json")
        .contains("\"no_metric_corruption_detected\": true"));
}

#[test]
fn maturity_remaining_demo_artifacts_are_internally_sane() {
    assert!(read_artifact("ScopeCoverageMatrix.json")
        .contains("\"hidden_regressions_detected\": false"));
    assert!(read_artifact("WitnessRevisionHistory.json")
        .contains("\"survived_hidden_failure_probe\": true"));
    assert!(read_artifact("DemotionReopeningTrace.jsonl").contains("\"demotion_allowed\":true"));
    assert!(read_artifact("ConstitutiveChangeLog.json").contains("\"declared\": true"));
    assert!(read_artifact("MaturationLogicStability.json")
        .contains("\"cross_domain_test_status\": \"passed\""));
    assert!(read_artifact("MaturationLogicStability.json").contains("tests/audit.rs"));
}

#[test]
fn c10_break_fix_closure_detects_break_and_revalidates_fix() {
    let _lock = blob_lock();
    write_demo_blob().expect("write demo blob");
    write_break_blob().expect("write break blob");
    assert!(detect_field_equality_break(&broken_evidence(), &witness()));

    let records = break_fix_records().expect("break/fix records");
    assert!(records
        .iter()
        .any(|record| record.kind() == "BreakFixTrialRecord"));
    assert!(records
        .iter()
        .any(|record| record.kind() == "RemediationAdviceRecord"));

    let path = std::env::temp_dir().join("icf-break-fix-test-ledger.jsonl");
    write_ledger(&path, &records).expect("write break/fix ledger");
    let content = std::fs::read_to_string(&path).expect("read break/fix ledger");
    std::fs::remove_file(&path).ok();
    verify_ledger_text(&content).expect("verify break/fix ledger");
}

#[test]
fn c13_remediation_is_advisory_and_requires_post_fix_evidence() {
    let post_fix = evidence();
    let mut advice = RemediationAdviceRecord {
        record_id: "remediation-1".to_string(),
        advice_id: "restore-banner-approved".to_string(),
        control_id: "demo.banner.approved".to_string(),
        advisory_only: true,
        post_fix_evidence_id: post_fix.record_id.clone(),
    };
    validate_remediation_advice(&advice, &post_fix, &witness()).expect("valid advice");

    advice.advisory_only = false;
    let err = validate_remediation_advice(&advice, &post_fix, &witness())
        .expect_err("non-advisory remediation must fail");
    assert!(err.contains("advisory_only"));
}

#[test]
fn c15_promotion_policy_refuses_insufficient_survivor_lineage() {
    let refused = evaluate_promotion("stig_expert_critic", 1, 2, false);
    assert_eq!(refused.decision, "REFUSED");

    let promoted = evaluate_promotion("stig_expert_critic", 2, 2, true);
    assert_eq!(promoted.decision, "PROMOTED");
}

#[test]
fn c9_witness_testability_rejects_bad_witness_and_survives_good_one() {
    let good = evaluate_witness_adequacy(&witness(), &broken_evidence());
    assert_eq!(good.status, "SURVIVED");

    let bad_witness = FieldEqualityWitness {
        witness_id: "demo.banner.approved.bad".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "DENIED".to_string(),
    };
    let bad = evaluate_witness_adequacy(&bad_witness, &broken_evidence());
    assert_eq!(bad.status, "REJECTED");
    assert!(bad.criticism.contains("hides seeded failure"));
}

#[test]
fn c11_synthesized_artifact_is_rejected_after_failed_witness_attack() {
    let bad_witness = FieldEqualityWitness {
        witness_id: "demo.banner.approved.synthetic".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "DENIED".to_string(),
    };
    let adequacy = evaluate_witness_adequacy(&bad_witness, &broken_evidence());
    let artifact = evaluate_synthesized_artifact("synth-validator-1", &adequacy);

    assert_eq!(artifact.status, "REJECTED");
    assert!(!artifact.promotion_allowed);
}

#[test]
fn c17_optimization_guardrail_rejects_visibility_or_falsifier_loss() {
    let safe = evaluate_optimization_guardrail("noop", true, true, true);
    assert!(safe.falsifier_yield_preserved);
    assert!(safe.evidence_visibility_preserved);
    assert!(safe.failure_visibility_preserved);

    let unsafe_candidate = evaluate_optimization_guardrail("drop-failures", true, true, false);
    assert!(!unsafe_candidate.failure_visibility_preserved);
}

#[test]
fn c19_contradiction_detection_records_claim_witness_evidence_mismatch() {
    let contradiction = detect_contradiction(&claim(), &witness(), &broken_evidence())
        .expect("broken evidence contradicts passing claim/witness");

    assert_eq!(
        contradiction.contradiction_kind,
        "claim_witness_evidence_mismatch"
    );
}

#[test]
fn c20_governance_requires_machine_policy_and_human_signoff() {
    let refused = evaluate_governance("stig_expert_critic", true, false);
    assert_eq!(refused.decision, "REFUSED");

    let approved = evaluate_governance("stig_expert_critic", true, true);
    assert_eq!(approved.decision, "APPROVED");
}

#[test]
fn c9_c11_c17_c19_c20_records_are_serializable() {
    let adequacy = evaluate_witness_adequacy(&witness(), &broken_evidence());
    let synthesized = evaluate_synthesized_artifact("synth-validator-1", &adequacy);
    let guardrail = evaluate_optimization_guardrail("noop", true, true, true);
    let contradiction =
        detect_contradiction(&claim(), &witness(), &broken_evidence()).expect("contradiction");
    let governance = evaluate_governance("stig_expert_critic", true, false);

    for record in [
        Record::WitnessAdequacy(adequacy),
        Record::SynthesizedArtifact(synthesized),
        Record::OptimizationGuardrail(guardrail),
        Record::Contradiction(contradiction),
        Record::GovernanceDecision(governance),
    ] {
        assert!(record.payload_json().contains("record_id"));
    }
}

#[test]
fn c14_replay_is_deterministic_and_offline_verifiable() {
    let _lock = blob_lock();
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-coalgebra-gate-ledger.jsonl");
    write_ledger(&path, &p0a_records().expect("records")).expect("write ledger");
    let first = std::fs::read_to_string(&path).expect("first read");
    write_ledger(&path, &p0a_records().expect("records")).expect("rewrite ledger");
    let second = std::fs::read_to_string(&path).expect("second read");
    std::fs::remove_file(&path).ok();

    assert_eq!(first, second);
    verify_ledger_text(&first).expect("offline verifier");
}

#[test]
fn c12_verifier_rejects_missing_or_tampered_evidence_blob() {
    let _lock = blob_lock();
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-coalgebra-blob-tamper.jsonl");
    write_ledger(&path, &p0a_records().expect("records")).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    std::fs::write(DEMO_BLOB_PATH, "TAMPERED").expect("tamper blob");
    let tampered = verify_ledger_text(&content).expect_err("tampered blob must fail");
    assert!(tampered.contains("evidence blob hash mismatch"));

    std::fs::remove_file(DEMO_BLOB_PATH).expect("remove blob");
    let missing = verify_ledger_text(&content).expect_err("missing blob must fail");
    assert!(missing.contains("evidence blob missing"));

    write_demo_blob().expect("restore demo blob");
}

#[test]
fn c16_ledger_rejects_removed_or_overwritten_failure_records() {
    let _lock = blob_lock();
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-coalgebra-ledger-tamper.jsonl");
    write_ledger(&path, &p0a_records().expect("records")).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let removed_falsifier = content
        .lines()
        .filter(|line| !line.contains("\"kind\":\"FalsifierRecord\""))
        .collect::<Vec<_>>()
        .join("\n");
    let err = verify_ledger_text(&removed_falsifier).expect_err("removed failure must fail");
    assert!(
        err.contains("prev_hash mismatch")
            || err.contains("record_hash mismatch")
            || err.contains("non-vacuous falsifier"),
        "{err}"
    );

    let overwritten = content.replace("DENIED", "HIDDEN");
    let err = verify_ledger_text(&overwritten).expect_err("overwritten failure must fail");
    assert!(err.contains("record_hash mismatch") || err.contains("evidence blob"));
}

#[test]
fn c18_direct_alignment_bypass_is_rejected() {
    let mut mismatched_claim = claim();
    mismatched_claim.control_id = "different.control".to_string();

    let err = run_field_equality_pullback(
        &mismatched_claim,
        &evidence(),
        &witness(),
        std::slice::from_ref(&falsifier()),
    )
    .expect_err("claim cannot bypass witness identity");

    assert!(err.contains("witness_id"));
}

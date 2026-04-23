use std::fs;
use std::path::Path;

use crate::ledger::write_ledger;
use crate::model::{
    detect_field_equality_break, evaluate_promotion, run_field_equality_pullback,
    validate_remediation_advice, BatchRecord, BreakFixTrialRecord, ClaimRecord, EvidenceRecord,
    FalsifierRecord, FieldEqualityWitness, Record, RemediationAdviceRecord, ScopeRecord,
};

pub const DEMO_BLOB_CONTENT: &str = "APPROVED";
pub const DEMO_BLOB_SHA256: &str =
    "f1995216dcfbca4efddfa35f22f1deceaa1d31ee7a829f9d6d72ed78a1aa258a";
pub const DEMO_BLOB_PATH: &str =
    "blobstore/demo/sha256/f1/995216dcfbca4efddfa35f22f1deceaa1d31ee7a829f9d6d72ed78a1aa258a";
pub const BREAK_BLOB_CONTENT: &str = "DENIED";
pub const BREAK_BLOB_SHA256: &str =
    "fc2efd7036582a0827d74e346366df1c1330d284f94d0db97e252aff1efdf1fa";
pub const BREAK_BLOB_PATH: &str =
    "blobstore/demo/sha256/fc/2efd7036582a0827d74e346366df1c1330d284f94d0db97e252aff1efdf1fa";

pub fn p0a_records() -> Result<Vec<Record>, String> {
    let witness = FieldEqualityWitness {
        witness_id: "demo.banner.approved".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "APPROVED".to_string(),
    };
    let scope = ScopeRecord {
        record_id: "scope-1".to_string(),
        platform: "F5 BIG-IP".to_string(),
        tmos_version: "fixture".to_string(),
        module: "LTM".to_string(),
        topology: "standalone".to_string(),
        credential_scope: "read-only fixture".to_string(),
    };
    let claim = ClaimRecord {
        record_id: "claim-1".to_string(),
        control_id: witness.witness_id.clone(),
        expected_value: witness.expected_literal.clone(),
    };
    let evidence = EvidenceRecord {
        record_id: "evidence-1".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: "APPROVED".to_string(),
        blob_path: DEMO_BLOB_PATH.to_string(),
        blob_sha256: DEMO_BLOB_SHA256.to_string(),
    };
    let falsifier = FalsifierRecord {
        record_id: "falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: witness.observable_field.clone(),
        counterexample_value: "DENIED".to_string(),
    };
    let pullback = run_field_equality_pullback(
        &claim,
        &evidence,
        &witness,
        std::slice::from_ref(&falsifier),
    )?;
    let batch = BatchRecord {
        record_id: "batch-1".to_string(),
        batch_id: "p0a-demo-batch".to_string(),
        committed: true,
    };

    Ok(vec![
        Record::Scope(scope),
        Record::Witness(witness),
        Record::Claim(claim),
        Record::Evidence(evidence),
        Record::Falsifier(falsifier),
        Record::Pullback(pullback),
        Record::Batch(batch),
    ])
}

pub fn write_p0a_demo_ledger(path: impl AsRef<Path>) -> Result<(), String> {
    write_demo_blob()?;
    write_ledger(path, &p0a_records()?)
}

pub fn break_fix_records() -> Result<Vec<Record>, String> {
    let witness = FieldEqualityWitness {
        witness_id: "demo.banner.approved".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "APPROVED".to_string(),
    };
    let scope = ScopeRecord {
        record_id: "scope-1".to_string(),
        platform: "F5 BIG-IP".to_string(),
        tmos_version: "fixture".to_string(),
        module: "LTM".to_string(),
        topology: "standalone".to_string(),
        credential_scope: "read-only fixture".to_string(),
    };
    let claim = ClaimRecord {
        record_id: "claim-1".to_string(),
        control_id: witness.witness_id.clone(),
        expected_value: witness.expected_literal.clone(),
    };
    let baseline = EvidenceRecord {
        record_id: "evidence-baseline".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: "APPROVED".to_string(),
        blob_path: DEMO_BLOB_PATH.to_string(),
        blob_sha256: DEMO_BLOB_SHA256.to_string(),
    };
    let broken = EvidenceRecord {
        record_id: "evidence-break".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: "DENIED".to_string(),
        blob_path: BREAK_BLOB_PATH.to_string(),
        blob_sha256: BREAK_BLOB_SHA256.to_string(),
    };
    let post_fix = EvidenceRecord {
        record_id: "evidence-post-fix".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: "APPROVED".to_string(),
        blob_path: DEMO_BLOB_PATH.to_string(),
        blob_sha256: DEMO_BLOB_SHA256.to_string(),
    };
    let falsifier = FalsifierRecord {
        record_id: "falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: witness.observable_field.clone(),
        counterexample_value: "DENIED".to_string(),
    };
    let mut baseline_pullback = run_field_equality_pullback(
        &claim,
        &baseline,
        &witness,
        std::slice::from_ref(&falsifier),
    )?;
    baseline_pullback.record_id = "pullback-baseline".to_string();
    let break_detected = detect_field_equality_break(&broken, &witness);
    let advice = RemediationAdviceRecord {
        record_id: "remediation-1".to_string(),
        advice_id: "restore-banner-approved".to_string(),
        control_id: witness.witness_id.clone(),
        advisory_only: true,
        post_fix_evidence_id: post_fix.record_id.clone(),
    };
    validate_remediation_advice(&advice, &post_fix, &witness)?;
    let mut post_fix_pullback = run_field_equality_pullback(
        &claim,
        &post_fix,
        &witness,
        std::slice::from_ref(&falsifier),
    )?;
    post_fix_pullback.record_id = "pullback-post-fix".to_string();
    let trial = BreakFixTrialRecord {
        record_id: "break-fix-trial-1".to_string(),
        trial_id: "trial-1".to_string(),
        control_id: witness.witness_id.clone(),
        baseline_evidence_id: baseline.record_id.clone(),
        break_evidence_id: broken.record_id.clone(),
        post_fix_evidence_id: post_fix.record_id.clone(),
        break_detected,
        fix_revalidated: true,
    };
    let promotion = evaluate_promotion("stig_expert_critic", 1, 2, false);
    let batch = BatchRecord {
        record_id: "batch-break-fix-1".to_string(),
        batch_id: "break-fix-demo-batch".to_string(),
        committed: true,
    };

    Ok(vec![
        Record::Scope(scope),
        Record::Witness(witness),
        Record::Claim(claim),
        Record::Evidence(baseline),
        Record::Falsifier(falsifier.clone()),
        Record::Pullback(baseline_pullback),
        Record::Evidence(broken),
        Record::BreakFixTrial(trial),
        Record::RemediationAdvice(advice),
        Record::Evidence(post_fix),
        Record::Pullback(post_fix_pullback),
        Record::PromotionDecision(promotion),
        Record::Batch(batch),
    ])
}

pub fn write_break_fix_demo_ledger(path: impl AsRef<Path>) -> Result<(), String> {
    write_demo_blob()?;
    write_break_blob()?;
    write_ledger(path, &break_fix_records()?)
}

pub fn write_demo_blob() -> Result<(), String> {
    let path = Path::new(DEMO_BLOB_PATH);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create {}: {err}", parent.display()))?;
    }
    fs::write(path, DEMO_BLOB_CONTENT)
        .map_err(|err| format!("failed to write {}: {err}", path.display()))
}

pub fn write_break_blob() -> Result<(), String> {
    let path = Path::new(BREAK_BLOB_PATH);
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create {}: {err}", parent.display()))?;
    }
    fs::write(path, BREAK_BLOB_CONTENT)
        .map_err(|err| format!("failed to write {}: {err}", path.display()))
}

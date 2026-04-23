use icf::demo::{
    break_fix_records, p0a_records, write_break_blob, write_demo_blob, DEMO_BLOB_PATH,
};
use icf::ledger::{verify_ledger_text, write_ledger};
use icf::model::{
    run_field_equality_pullback, ClaimRecord, EvidenceRecord, FalsifierRecord,
    FieldEqualityWitness, Record,
};

#[test]
fn p0a_records_verify_after_write() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-test-ledger.jsonl");
    write_ledger(&path, &p0a_records().expect("records")).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    verify_ledger_text(&content).expect("ledger verifies");
}

#[test]
fn verifier_rejects_missing_required_p0a_record_type() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-missing-batch-ledger.jsonl");
    let records: Vec<_> = p0a_records()
        .expect("records")
        .into_iter()
        .filter(|record| record.kind() != "BatchRecord")
        .collect();
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("missing committed batch must fail");
    assert!(err.contains("committed BatchRecord"));
}

#[test]
fn verifier_rejects_records_after_committed_batch() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-trailing-record-ledger.jsonl");
    let mut records = p0a_records().expect("records");
    let trailing_claim = records
        .iter()
        .find(|record| record.kind() == "ClaimRecord")
        .expect("claim")
        .clone();
    records.push(trailing_claim);
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("trailing record must fail");
    assert!(err.contains("after committed BatchRecord"));
}

#[test]
fn verifier_rejects_pullback_before_supporting_records() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-early-pullback-ledger.jsonl");
    let mut records = p0a_records().expect("records");
    let pullback_index = records
        .iter()
        .position(|record| record.kind() == "PullbackRecord")
        .expect("pullback");
    let pullback = records.remove(pullback_index);
    records.insert(0, pullback);
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("early pullback must fail");
    assert!(err.contains("requires prior scope, witness, claim, and evidence"));
}

#[test]
fn verifier_rejects_pullback_with_unknown_claim_reference() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-bad-pullback-xref-ledger.jsonl");
    let mut records = p0a_records().expect("records");
    for record in &mut records {
        if let Record::Pullback(pullback) = record {
            pullback.claim_id = "missing-claim".to_string();
        }
    }
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("unknown claim reference must fail");
    assert!(err.contains("unknown claim_id missing-claim"));
}

#[test]
fn verifier_rejects_duplicate_record_id() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-duplicate-id-ledger.jsonl");
    let mut records = p0a_records().expect("records");
    let claim_index = records
        .iter()
        .position(|record| record.kind() == "ClaimRecord")
        .expect("claim");
    let duplicate_claim = records[claim_index].clone();
    records.insert(claim_index + 1, duplicate_claim);
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("duplicate record_id must fail");
    assert!(err.contains("duplicate record_id claim-1"));
}

#[test]
fn verifier_recomputes_pullback_judgment_semantics() {
    write_demo_blob().expect("write demo blob");
    let path = std::env::temp_dir().join("icf-p0a-bad-pullback-semantics-ledger.jsonl");
    let mut records = p0a_records().expect("records");
    for record in &mut records {
        if let Record::Evidence(evidence) = record {
            evidence.observed_value = "DENIED".to_string();
        }
    }
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("semantic mismatch must fail");
    assert!(err.contains("judgment_state mismatch"));
}

#[test]
fn verifier_rejects_break_fix_trial_with_unknown_evidence_reference() {
    write_demo_blob().expect("write demo blob");
    write_break_blob().expect("write break blob");
    let path = std::env::temp_dir().join("icf-break-fix-bad-xref-ledger.jsonl");
    let mut records = break_fix_records().expect("records");
    for record in &mut records {
        if let Record::BreakFixTrial(trial) = record {
            trial.break_evidence_id = "missing-break-evidence".to_string();
        }
    }
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("unknown break evidence must fail");
    assert!(err.contains("unknown break_evidence_id missing-break-evidence"));
}

#[test]
fn verifier_rejects_forged_promotion_decision() {
    write_demo_blob().expect("write demo blob");
    write_break_blob().expect("write break blob");
    let path = std::env::temp_dir().join("icf-break-fix-forged-promotion-ledger.jsonl");
    let mut records = break_fix_records().expect("records");
    for record in &mut records {
        if let Record::PromotionDecision(promotion) = record {
            promotion.decision = "PROMOTED".to_string();
        }
    }
    write_ledger(&path, &records).expect("write ledger");
    let content = std::fs::read_to_string(&path).expect("read ledger");
    std::fs::remove_file(&path).ok();

    let err = verify_ledger_text(&content).expect_err("forged promotion must fail");
    assert!(err.contains("PromotionDecisionRecord decision mismatch"));
}

#[test]
fn pass_requires_non_vacuous_falsifier() {
    let witness = FieldEqualityWitness {
        witness_id: "demo.banner.approved".to_string(),
        observable_field: "banner_text".to_string(),
        expected_literal: "APPROVED".to_string(),
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
        blob_sha256: icf::demo::DEMO_BLOB_SHA256.to_string(),
    };
    let vacuous = FalsifierRecord {
        record_id: "falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: String::new(),
        counterexample_value: String::new(),
    };

    let err = run_field_equality_pullback(&claim, &evidence, &witness, &[vacuous])
        .expect_err("vacuous falsifier must be rejected");

    assert!(err.contains("non-vacuous falsifier"));
}

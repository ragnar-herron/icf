//! Live F5 break/fix adapter.
//!
//! This module is the counterpart to `src/demo.rs`: it consumes a live
//! evidence manifest (produced by `scripts/live_break_fix.py` after it has
//! actually spoken to a real F5 BIG-IP over iControl REST) and emits a
//! ledger that is byte-for-byte the same shape as the demo ledger, so the
//! existing offline verifier (`src/ledger.rs::verify_ledger_text`) is the
//! sole authority on whether the live run is truth-shaped.
//!
//! The kernel functions `run_field_equality_pullback`,
//! `detect_field_equality_break`, `validate_remediation_advice`, and
//! `evaluate_promotion` are imported verbatim from `src/model.rs`. There
//! is no live-specific predicate logic here — the "live-ness" is entirely
//! in the evidence (content-addressed blobs fetched from the real device),
//! not in the judgment.

use std::fs;
use std::path::Path;

use crate::ledger::{sha256_hex, write_ledger};
use crate::model::{
    detect_field_equality_break, evaluate_promotion, run_field_equality_pullback,
    validate_remediation_advice, BatchRecord, BreakFixTrialRecord, ClaimRecord, EvidenceRecord,
    FalsifierRecord, FieldEqualityWitness, Record, RemediationAdviceRecord, ScopeRecord,
};

pub fn build_live_break_fix_ledger(
    manifest_path: impl AsRef<Path>,
    out_path: impl AsRef<Path>,
) -> Result<LiveRunSummary, String> {
    let manifest = fs::read_to_string(manifest_path.as_ref())
        .map_err(|err| format!("failed to read {}: {err}", manifest_path.as_ref().display()))?;

    let platform = required_string(&manifest, "scope_platform")?;
    let tmos_version = required_string(&manifest, "scope_tmos_version")?;
    let module = required_string(&manifest, "scope_module")?;
    let topology = required_string(&manifest, "scope_topology")?;
    let credential_scope = required_string(&manifest, "scope_credential_scope")?;
    let host = required_string(&manifest, "scope_host")?;
    let hostname = required_string(&manifest, "scope_hostname")?;

    let witness_id = required_string(&manifest, "witness_id")?;
    let witness_field = required_string(&manifest, "witness_observable_field")?;
    let expected_blob_path = required_string(&manifest, "witness_expected_blob_path")?;

    let baseline_blob_path = required_string(&manifest, "baseline_blob_path")?;
    let baseline_blob_sha256 = required_string(&manifest, "baseline_blob_sha256")?;
    let break_blob_path = required_string(&manifest, "break_blob_path")?;
    let break_blob_sha256 = required_string(&manifest, "break_blob_sha256")?;
    let post_fix_blob_path = required_string(&manifest, "post_fix_blob_path")?;
    let post_fix_blob_sha256 = required_string(&manifest, "post_fix_blob_sha256")?;
    let started_at = required_string(&manifest, "started_at")?;
    let stig_probe_matches = required_string(&manifest, "stig_probe_matches")?;
    let stig_probe_expected_sha256 = required_string(&manifest, "stig_probe_expected_sha256")?;

    let expected_literal = read_blob_string(&expected_blob_path)?;
    let baseline_observed =
        read_blob_string_and_verify(&baseline_blob_path, &baseline_blob_sha256)?;
    let break_observed = read_blob_string_and_verify(&break_blob_path, &break_blob_sha256)?;
    let post_fix_observed =
        read_blob_string_and_verify(&post_fix_blob_path, &post_fix_blob_sha256)?;

    if baseline_observed != expected_literal {
        return Err(
            "baseline observed value must equal the expected literal blob (witness calibrated to baseline)"
                .to_string(),
        );
    }
    if post_fix_observed != expected_literal {
        return Err(
            "post-fix observed value must equal the expected literal (restore must be byte-identical)"
                .to_string(),
        );
    }
    if break_observed == expected_literal {
        return Err("break observed value must differ from the expected literal".to_string());
    }

    let witness = FieldEqualityWitness {
        witness_id: witness_id.clone(),
        observable_field: witness_field.clone(),
        expected_literal,
    };
    let scope = ScopeRecord {
        record_id: "live-scope-1".to_string(),
        platform,
        tmos_version: tmos_version.clone(),
        module,
        topology,
        credential_scope: format!(
            "{credential_scope} | host={host} hostname={hostname} started_at={started_at}"
        ),
    };
    let claim = ClaimRecord {
        record_id: "live-claim-1".to_string(),
        control_id: witness.witness_id.clone(),
        expected_value: witness.expected_literal.clone(),
    };
    let baseline_evidence = EvidenceRecord {
        record_id: "live-evidence-baseline".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: baseline_observed.clone(),
        blob_path: baseline_blob_path.clone(),
        blob_sha256: baseline_blob_sha256.clone(),
    };
    let break_evidence = EvidenceRecord {
        record_id: "live-evidence-break".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: break_observed.clone(),
        blob_path: break_blob_path.clone(),
        blob_sha256: break_blob_sha256.clone(),
    };
    let post_fix_evidence = EvidenceRecord {
        record_id: "live-evidence-post-fix".to_string(),
        field_name: witness.observable_field.clone(),
        observed_value: post_fix_observed.clone(),
        blob_path: post_fix_blob_path.clone(),
        blob_sha256: post_fix_blob_sha256.clone(),
    };
    let falsifier = FalsifierRecord {
        record_id: "live-falsifier-1".to_string(),
        family: "observational".to_string(),
        counterexample_field: witness.observable_field.clone(),
        counterexample_value: break_observed.clone(),
    };

    let mut baseline_pullback = run_field_equality_pullback(
        &claim,
        &baseline_evidence,
        &witness,
        std::slice::from_ref(&falsifier),
    )?;
    baseline_pullback.record_id = "live-pullback-baseline".to_string();

    let break_detected = detect_field_equality_break(&break_evidence, &witness);
    if !break_detected {
        return Err("kernel did not detect break on live break evidence".to_string());
    }

    let advice = RemediationAdviceRecord {
        record_id: "live-remediation-1".to_string(),
        advice_id: format!("restore-{}-to-baseline", witness.observable_field),
        control_id: witness.witness_id.clone(),
        advisory_only: true,
        post_fix_evidence_id: post_fix_evidence.record_id.clone(),
    };
    validate_remediation_advice(&advice, &post_fix_evidence, &witness)?;

    let mut post_fix_pullback = run_field_equality_pullback(
        &claim,
        &post_fix_evidence,
        &witness,
        std::slice::from_ref(&falsifier),
    )?;
    post_fix_pullback.record_id = "live-pullback-post-fix".to_string();

    let trial = BreakFixTrialRecord {
        record_id: "live-break-fix-trial-1".to_string(),
        trial_id: "live-trial-1".to_string(),
        control_id: witness.witness_id.clone(),
        baseline_evidence_id: baseline_evidence.record_id.clone(),
        break_evidence_id: break_evidence.record_id.clone(),
        post_fix_evidence_id: post_fix_evidence.record_id.clone(),
        break_detected,
        fix_revalidated: true,
    };

    // Live promotion: one trial survived on a real device, but human
    // signoff is NOT present, so the kernel refuses promotion. This is
    // the correct answer: a single successful live trial is far from
    // enough to promote a witness or a validator into production.
    let promotion = evaluate_promotion(&format!("live_f5_{hostname}"), 1, 3, false);
    let batch = BatchRecord {
        record_id: "live-batch-1".to_string(),
        batch_id: format!("live-break-fix-{tmos_version}"),
        committed: true,
    };

    let records = vec![
        Record::Scope(scope),
        Record::Witness(witness.clone()),
        Record::Claim(claim),
        Record::Evidence(baseline_evidence),
        Record::Falsifier(falsifier),
        Record::Pullback(baseline_pullback),
        Record::Evidence(break_evidence),
        Record::BreakFixTrial(trial),
        Record::RemediationAdvice(advice),
        Record::Evidence(post_fix_evidence),
        Record::Pullback(post_fix_pullback),
        Record::PromotionDecision(promotion),
        Record::Batch(batch),
    ];

    write_ledger(out_path.as_ref(), &records)?;

    Ok(LiveRunSummary {
        out_path: out_path.as_ref().display().to_string(),
        host,
        hostname,
        tmos_version,
        observable_field: witness.observable_field,
        baseline_blob_sha256,
        break_blob_sha256,
        post_fix_blob_sha256,
        record_count: records.len(),
        stig_probe_matches: stig_probe_matches == "true",
        stig_probe_expected_sha256,
    })
}

#[derive(Debug)]
pub struct LiveRunSummary {
    pub out_path: String,
    pub host: String,
    pub hostname: String,
    pub tmos_version: String,
    pub observable_field: String,
    pub baseline_blob_sha256: String,
    pub break_blob_sha256: String,
    pub post_fix_blob_sha256: String,
    pub record_count: usize,
    pub stig_probe_matches: bool,
    pub stig_probe_expected_sha256: String,
}

impl LiveRunSummary {
    pub fn to_markdown(&self) -> String {
        let mut output = String::new();
        output.push_str("# Live F5 break/fix run summary\n\n");
        output.push_str(&format!("- host: `{}`\n", self.host));
        output.push_str(&format!("- hostname: `{}`\n", self.hostname));
        output.push_str(&format!("- tmos_version: `{}`\n", self.tmos_version));
        output.push_str(&format!(
            "- observable_field: `{}`\n",
            self.observable_field
        ));
        output.push_str(&format!("- records: {}\n", self.record_count));
        output.push_str(&format!("- ledger: `{}`\n", self.out_path));
        output.push_str(&format!(
            "- baseline blob sha256: `{}`\n",
            self.baseline_blob_sha256
        ));
        output.push_str(&format!(
            "- break blob sha256: `{}` (must differ from baseline)\n",
            self.break_blob_sha256
        ));
        output.push_str(&format!(
            "- post-fix blob sha256: `{}` (must equal baseline)\n",
            self.post_fix_blob_sha256
        ));
        let stig_verdict = if self.stig_probe_matches {
            "PASS (device baseline matches canonical DoD Notice and Consent Banner)"
        } else {
            "FAIL (device baseline does NOT match canonical DoD Notice and Consent Banner; \
             this is a device-compliance observation, not a live-run failure)"
        };
        output.push_str(&format!("- STIG banner witness probe: {}\n", stig_verdict));
        output.push_str(&format!(
            "- STIG witness expected SHA-256: `{}`\n",
            self.stig_probe_expected_sha256
        ));
        output
    }
}

fn read_blob_string(rel: &str) -> Result<String, String> {
    fs::read_to_string(rel).map_err(|err| format!("failed to read blob {rel}: {err}"))
}

fn read_blob_string_and_verify(rel: &str, expected_hash: &str) -> Result<String, String> {
    let bytes = fs::read(rel).map_err(|err| format!("failed to read blob {rel}: {err}"))?;
    let actual = sha256_hex(&bytes);
    if actual != expected_hash {
        return Err(format!(
            "blob hash mismatch for {rel}: expected {expected_hash}, got {actual}"
        ));
    }
    String::from_utf8(bytes).map_err(|err| format!("blob {rel} is not valid UTF-8: {err}"))
}

fn required_string(input: &str, key: &str) -> Result<String, String> {
    let needle = format!("\"{key}\"");
    let start = input
        .find(&needle)
        .ok_or_else(|| format!("manifest missing key `{key}`"))?;
    let after = &input[start + needle.len()..];
    let colon = after
        .find(':')
        .ok_or_else(|| format!("manifest missing `:` after key `{key}`"))?;
    let value = after[colon + 1..].trim_start();
    let rest = value
        .strip_prefix('"')
        .ok_or_else(|| format!("manifest key `{key}` must be a string"))?;
    let end = rest
        .find('"')
        .ok_or_else(|| format!("manifest key `{key}` string is unterminated"))?;
    Ok(rest[..end].to_string())
}

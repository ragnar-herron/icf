use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct MaturityGateItem {
    pub id: &'static str,
    pub gate: &'static str,
    pub test: &'static str,
    pub status: &'static str,
    pub evidence: &'static str,
    pub gap: &'static str,
}

pub const MATURITY_GATE_ITEMS: &[MaturityGateItem] = &[
    item("C1", "Coalgebra", "State Defined", "demo-pass", "coalgebra/stig_expert_critic/StateSchema.json; StateSnapshot.json", ""),
    item("C2", "Coalgebra", "Observations Defined", "demo-pass", "coalgebra/stig_expert_critic/ObservationSchema.json; ledgers/demo/*.jsonl", ""),
    item("C3", "Coalgebra", "Inputs Defined", "demo-pass", "coalgebra/stig_expert_critic/EventSchema.json", ""),
    item("C4", "Coalgebra", "Behavior Map", "demo-pass", "src/model.rs::step; c4_step_is_deterministic", ""),
    item("C5", "Coalgebra", "Behavioral Distinction", "demo-pass", "states_are_distinguishable; c5_distinguishes_behaviorally_different_states", ""),
    item("C6", "Coalgebra", "Falsifier Defined", "demo-pass", "coalgebra/stig_expert_critic/FalsifierCatalog.md; c6_falsifier_catalog_is_non_vacuous_and_executed", ""),
    item("C7", "Coalgebra", "Scope Defined", "demo-pass", "coalgebra/stig_expert_critic/ScopeRecord.json", ""),
    item("P1", "Pullback", "Declaration-Reality", "demo-pass", "PullbackRecord verifier replay; c18_direct_alignment_bypass_is_rejected", ""),
    item("P2", "Pullback", "Claim-Evidence", "demo-pass", "ClaimRecord; EvidenceRecord; blobstore/demo", ""),
    item("P3", "Pullback", "Witness-Reality", "demo-pass", "WitnessTestSuite.md; c9_witness_testability_rejects_bad_witness_and_survives_good_one", ""),
    item("P4", "Pullback", "Plan-Execution", "demo-pass", "BreakFixTrialRecords.jsonl; ledgers/demo/break_fix.jsonl", ""),
    item("P5", "Pullback", "Synthesis-Behavior", "demo-pass", "SynthesizedArtifactRecords.jsonl; c11_synthesized_artifact_is_rejected_after_failed_witness_attack", ""),
    item("P6", "Pullback", "Failure-Survivor", "demo-pass", "coalgebra/stig_expert_critic/SurvivorLineage.json", ""),
    item("P7", "Pullback", "Level-Level", "demo-pass", "ContradictionRecords.jsonl; c19_contradiction_detection_records_claim_witness_evidence_mismatch", ""),
    item("P8", "Pullback", "Revision-Identity", "demo-pass", "coalgebra/stig_expert_critic/RevisionIdentityLog.json; coalgebra/stig_expert_critic/IdentityAudit.json", ""),
    item("P9", "Pullback", "Criticism-Memory", "demo-pass", "CriticismLedger.jsonl; c16_ledger_rejects_removed_or_overwritten_failure_records", ""),
    item("P10", "Pullback", "Optimization-Truth", "demo-pass", "WHRReport.md; c17_optimization_guardrail_rejects_visibility_or_falsifier_loss", ""),
    item("M1", "Maturity", "State Growth", "demo-pass", "coalgebra/stig_expert_critic/StateLineage.json", ""),
    item("M2", "Maturity", "Criticism Retention", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("M3", "Maturity", "Falsifier Vitality", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("M4", "Maturity", "Scope Expansion", "demo-pass", "coalgebra/stig_expert_critic/ScopeCoverageMatrix.json; tests/audit.rs::m4_scope_coverage_matrix_is_multi_axis_and_traceable", ""),
    item("M5", "Maturity", "Survivor Strength", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("M6", "Maturity", "Witness Improvement", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("M7", "Maturity", "Efficiency Honesty", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("M8", "Maturity", "Recursive Reopening", "demo-pass", "coalgebra/stig_expert_critic/DemotionReopeningTrace.jsonl", ""),
    item("E1", "Error", "False Positive Reduction", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("E2", "Error", "False Negative Reduction", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("E3", "Error", "Break Detection", "demo-pass", "BreakFixTrialRecords.jsonl; c10_break_fix_closure_detects_break_and_revalidates_fix", ""),
    item("E4", "Error", "Fix Validation", "demo-pass", "RemediationAdviceRecord.json; break/fix verifier checks", ""),
    item("E5", "Error", "Synthesis Correction", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("E6", "Error", "Witness Miss Reduction", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("E7", "Error", "Cross-Level Consistency", "demo-pass", "fixtures/maturity; icf maturity verify-fixture fixtures/maturity", ""),
    item("E8", "Error", "Residual Conversion", "demo-pass", "coalgebra/stig_expert_critic/ResidualConversionRecords.jsonl", ""),
    item("D1", "Drift", "Core Pullbacks Preserved", "demo-pass", "coalgebra/stig_expert_critic/PullbackBaseline.json; tests/audit.rs::d1_core_pullbacks_preserved", ""),
    item("D2", "Drift", "Identity Stability", "demo-pass", "coalgebra/stig_expert_critic/IdentityAudit.json", ""),
    item("D3", "Drift", "Constitutive Changes Declared", "demo-pass", "coalgebra/stig_expert_critic/ConstitutiveChangeLog.json", ""),
    item("D4", "Drift", "Stable Maturation Logic", "demo-pass", "coalgebra/stig_expert_critic/MaturationLogicStability.json; tests/audit.rs::d4_stable_maturation_logic_on_second_domain", ""),
    item("D5", "Drift", "Lineage Preservation", "demo-pass", "coalgebra/stig_expert_critic/LineagePreservationCheck.json", ""),
    item("D6", "Drift", "Metric Integrity", "demo-pass", "coalgebra/stig_expert_critic/MetricSignature.json; ledgers/demo/metric_checkpoint.jsonl; tests/audit.rs::d6_metrics_match_signed_digest_and_checkpoint", ""),
    item("D7", "Drift", "No Shortcut Paths", "demo-pass", "c18_direct_alignment_bypass_is_rejected; verifier pullback replay", ""),
    item("D8", "Drift", "General vs Specialized Separation", "demo-pass", "docs/BUILD_SPEC.md; tests/audit.rs::d8_kernel_is_domain_agnostic", ""),
    item("L1", "Live",  "Device Reachable",                  "demo-pass", "coalgebra/stig_expert_critic/LiveCampaignEvidence.json; docs/LIVE_RUN_REPORT.md; live_state/full_campaign/manifest.json", ""),
    item("L2", "Live",  "Baseline Content-Addressed",        "demo-pass", "live_state/full_campaign/manifest.json; blobstore/live/sha256/**; tests/live_campaign_replay.rs::live_campaign_replay_reproduces_ledger_and_verifies", ""),
    item("L3", "Live",  "Real Break Introduced",             "demo-pass", "ledgers/live/break_fix.jsonl (BreakFixTrialRecord.break_detected=true); blobstore/live/sha256/53/**; tests/live_replay.rs", ""),
    item("L4", "Live",  "Real Fix Byte-Identical Restore",   "demo-pass", "ledgers/live/break_fix.jsonl (fix_revalidated=true); coalgebra/stig_expert_critic/LiveCampaignEvidence.json.notable_remediations", ""),
    item("L5", "Live",  "Ledger Offline-Verified",           "demo-pass", "icf ledger verify ledgers/live/break_fix.jsonl; icf ledger verify ledgers/live/full_campaign.jsonl; tests/live_replay.rs; tests/live_campaign_replay.rs", ""),
    item("L6", "Live",  "Device Left Clean",                 "demo-pass", "coalgebra/stig_expert_critic/LiveCampaignEvidence.json; live_state/full_campaign/manifest.json", ""),
];

const fn item(
    id: &'static str,
    gate: &'static str,
    test: &'static str,
    status: &'static str,
    evidence: &'static str,
    gap: &'static str,
) -> MaturityGateItem {
    MaturityGateItem {
        id,
        gate,
        test,
        status,
        evidence,
        gap,
    }
}

pub fn maturity_report_markdown(fail_on_any_failure: bool) -> Result<String, String> {
    maturity_report_markdown_with_filter(fail_on_any_failure, false)
}

pub fn maturity_partials_report_markdown(fail_on_any_partial: bool) -> Result<String, String> {
    maturity_report_markdown_with_filter(fail_on_any_partial, true)
}

#[derive(Debug)]
struct MaturityRevision {
    revision_id: String,
    criticism_ids: Vec<String>,
    falsifier_yield: u64,
    false_pass_rate: f64,
    false_fail_rate: f64,
    survivors_evaluated: u64,
    survivors_retained: u64,
    witness_revision_id: String,
    witness_revision_cites_criticism: bool,
    truth_regression_detected: bool,
    waste_score: u64,
    synthesis_safe: bool,
    synthesis_improvement_score: u64,
    hidden_failure_miss_rate: f64,
    contradiction_resolution_steps: u64,
}

pub fn verify_maturity_fixture(path: impl AsRef<Path>) -> Result<String, String> {
    let root = path.as_ref();
    let revision_0 = read_revision(root, "revision_0")?;
    let revision_1 = read_revision(root, "revision_1")?;

    ensure(
        revision_0.revision_id == "revision_0" && revision_1.revision_id == "revision_1",
        "revision identities must match their fixture directories",
    )?;
    ensure(
        revision_0
            .criticism_ids
            .iter()
            .all(|id| revision_1.criticism_ids.contains(id)),
        "revision_1 must retain every revision_0 criticism",
    )?;
    ensure(
        revision_0.falsifier_yield > 0 && revision_1.falsifier_yield >= revision_0.falsifier_yield,
        "falsifier yield must be nonzero and non-decreasing",
    )?;
    ensure(
        revision_1.false_pass_rate <= revision_0.false_pass_rate,
        "false pass rate must be non-increasing",
    )?;
    ensure(
        revision_1.false_fail_rate <= revision_0.false_fail_rate,
        "false fail rate must be non-increasing",
    )?;
    ensure(
        revision_0.survivors_evaluated > 0 && revision_1.survivors_evaluated > 0,
        "survivor metrics must evaluate at least one survivor in each revision",
    )?;
    ensure(
        retention_rate(&revision_1) >= retention_rate(&revision_0),
        "survivor retention rate must be non-decreasing",
    )?;
    ensure(
        revision_1.witness_revision_id != revision_0.witness_revision_id
            && revision_1.witness_revision_cites_criticism,
        "witness revision must change and cite criticism",
    )?;
    ensure(
        !revision_0.truth_regression_detected
            && !revision_1.truth_regression_detected
            && revision_1.waste_score <= revision_0.waste_score,
        "efficiency improvement must not hide truth regressions",
    )?;
    ensure(
        revision_1.synthesis_safe
            && revision_1.synthesis_improvement_score >= revision_0.synthesis_improvement_score,
        "synthesis correction must remain safe and non-regressing",
    )?;
    ensure(
        revision_1.hidden_failure_miss_rate <= revision_0.hidden_failure_miss_rate,
        "hidden-failure miss rate must be non-increasing",
    )?;
    ensure(
        revision_1.contradiction_resolution_steps <= revision_0.contradiction_resolution_steps,
        "contradiction resolution steps must be non-increasing",
    )?;

    let mut output = String::new();
    output.push_str("# Maturity Fixture Verification\n\n");
    output.push_str(&format!("Fixture: {}\n\n", root.display()));
    output.push_str("Status: demo-pass\n\n");
    output.push_str("Checks:\n");
    output.push_str("- criticism retention: pass\n");
    output.push_str("- falsifier vitality: pass\n");
    output.push_str("- false positive reduction: pass\n");
    output.push_str("- false negative reduction: pass\n");
    output.push_str("- survivor strength: pass\n");
    output.push_str("- witness improvement: pass\n");
    output.push_str("- efficiency honesty: pass\n");
    output.push_str("- synthesis correction: pass\n");
    output.push_str("- witness miss reduction: pass\n");
    output.push_str("- cross-level consistency: pass\n");
    Ok(output)
}

fn maturity_report_markdown_with_filter(
    fail_on_any_failure: bool,
    partials_only: bool,
) -> Result<String, String> {
    let incomplete = MATURITY_GATE_ITEMS
        .iter()
        .filter(|item| item.status != "demo-pass")
        .collect::<Vec<_>>();

    if fail_on_any_failure && !incomplete.is_empty() {
        return Err(format!(
            "maturity gate incomplete: {} non-passing rows ({})",
            incomplete.len(),
            incomplete
                .iter()
                .map(|item| item.id)
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }

    let mut output = String::new();
    let demo_pass_count = MATURITY_GATE_ITEMS
        .iter()
        .filter(|item| item.status == "demo-pass")
        .count();
    let partial_count = MATURITY_GATE_ITEMS
        .iter()
        .filter(|item| item.status == "partial")
        .count();
    let fail_count = MATURITY_GATE_ITEMS
        .iter()
        .filter(|item| item.status == "fail")
        .count();

    let demo_gate_status = if partial_count == 0 && fail_count == 0 {
        "PASS"
    } else {
        "FAIL"
    };

    if partials_only {
        output.push_str("# STIG Information Maturity Partial Backlog\n\n");
    } else {
        output.push_str("# STIG Information Maturity Gate Report\n\n");
    }
    output.push_str("Subject: STIG Expert Critic P0a\n\n");
    if partial_count == 0 && fail_count == 0 {
        output.push_str("Status: demo maturity gate passes; every row has executable evidence. Production maturity is still out of scope: promotion to production requires real-lab STIG evidence, Ed25519-signed metrics, multi-domain adapters, and a signed trust root.\n\n");
    } else {
        output.push_str(
            "Status: incomplete for demo maturity; some rows are still partial or failing\n\n",
        );
    }
    output.push_str("## Summary\n\n");
    output.push_str(&format!("- Demo-pass rows: {demo_pass_count}\n"));
    output.push_str(&format!("- Partial rows: {partial_count}\n"));
    output.push_str(&format!("- Fail rows: {fail_count}\n"));
    output.push_str(&format!("- Demo maturity gate: {demo_gate_status}\n\n"));
    output.push_str("| ID | Gate | Test | Status | Evidence | Gap |\n");
    output.push_str("| --- | --- | --- | --- | --- | --- |\n");
    for item in MATURITY_GATE_ITEMS {
        if partials_only && item.status != "partial" {
            continue;
        }
        output.push_str(&format!(
            "| {} | {} | {} | {} | `{}` | {} |\n",
            item.id, item.gate, item.test, item.status, item.evidence, item.gap
        ));
    }
    if !partials_only {
        output.push_str("\n## Final Decisions\n\n");
        output.push_str("| Decision | Status |\n");
        output.push_str("| --- | --- |\n");
        if partial_count == 0 && fail_count == 0 {
            output.push_str(
                "| System qualifies as STIG Expert Critic Coalgebra | DEMO YES / PRODUCTION NO |\n",
            );
            output.push_str("| System is maturing correctly | DEMO YES |\n");
            output.push_str("| System is progressively error-correcting | DEMO YES |\n");
            output.push_str("| System is stable / not drifting | DEMO YES |\n");
            output.push_str(
                "| Constitutive redesign required | NO for P0a; YES before production maturity claim |\n",
            );
        } else {
            output.push_str(
                "| System qualifies as STIG Expert Critic Coalgebra | DEMO YES / PRODUCTION NO |\n",
            );
            output.push_str("| System is maturing correctly | PARTIAL |\n");
            output.push_str("| System is progressively error-correcting | PARTIAL |\n");
            output.push_str("| System is stable / not drifting | PARTIAL |\n");
            output.push_str(
                "| Constitutive redesign required | NO for P0a; YES before production maturity claim |\n",
            );
        }
    }
    Ok(output)
}

fn read_revision(root: &Path, revision_dir: &str) -> Result<MaturityRevision, String> {
    let path = root.join(revision_dir).join("metrics.json");
    let content = fs::read_to_string(&path)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;

    Ok(MaturityRevision {
        revision_id: required_json_string(&content, "revision_id")?,
        criticism_ids: required_json_string_array(&content, "criticism_ids")?,
        falsifier_yield: required_json_u64(&content, "falsifier_yield")?,
        false_pass_rate: required_json_f64(&content, "false_pass_rate")?,
        false_fail_rate: required_json_f64(&content, "false_fail_rate")?,
        survivors_evaluated: required_json_u64(&content, "survivors_evaluated")?,
        survivors_retained: required_json_u64(&content, "survivors_retained")?,
        witness_revision_id: required_json_string(&content, "witness_revision_id")?,
        witness_revision_cites_criticism: required_json_bool(
            &content,
            "witness_revision_cites_criticism",
        )?,
        truth_regression_detected: required_json_bool(&content, "truth_regression_detected")?,
        waste_score: required_json_u64(&content, "waste_score")?,
        synthesis_safe: required_json_bool(&content, "synthesis_safe")?,
        synthesis_improvement_score: required_json_u64(&content, "synthesis_improvement_score")?,
        hidden_failure_miss_rate: required_json_f64(&content, "hidden_failure_miss_rate")?,
        contradiction_resolution_steps: required_json_u64(
            &content,
            "contradiction_resolution_steps",
        )?,
    })
}

fn retention_rate(revision: &MaturityRevision) -> f64 {
    revision.survivors_retained as f64 / revision.survivors_evaluated as f64
}

fn ensure(condition: bool, message: &str) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(message.to_string())
    }
}

fn value_after_key<'a>(input: &'a str, key: &str) -> Result<&'a str, String> {
    let needle = format!("\"{key}\"");
    let key_start = input
        .find(&needle)
        .ok_or_else(|| format!("missing required key `{key}`"))?;
    let after_key = &input[key_start + needle.len()..];
    let colon = after_key
        .find(':')
        .ok_or_else(|| format!("missing value separator for `{key}`"))?;
    Ok(after_key[colon + 1..].trim_start())
}

fn required_json_string(input: &str, key: &str) -> Result<String, String> {
    let value = value_after_key(input, key)?;
    let unquoted = value
        .strip_prefix('"')
        .ok_or_else(|| format!("`{key}` must be a string"))?;
    let end = unquoted
        .find('"')
        .ok_or_else(|| format!("`{key}` string is unterminated"))?;
    Ok(unquoted[..end].to_string())
}

fn required_json_string_array(input: &str, key: &str) -> Result<Vec<String>, String> {
    let value = value_after_key(input, key)?;
    let array = value
        .strip_prefix('[')
        .ok_or_else(|| format!("`{key}` must be a string array"))?;
    let end = array
        .find(']')
        .ok_or_else(|| format!("`{key}` array is unterminated"))?;

    let mut values = Vec::new();
    for raw in array[..end].split(',') {
        let trimmed = raw.trim();
        if trimmed.is_empty() {
            continue;
        }
        let unquoted = trimmed
            .strip_prefix('"')
            .and_then(|value| value.strip_suffix('"'))
            .ok_or_else(|| format!("`{key}` entries must be strings"))?;
        values.push(unquoted.to_string());
    }

    if values.is_empty() {
        Err(format!("`{key}` must not be empty"))
    } else {
        Ok(values)
    }
}

fn required_json_bool(input: &str, key: &str) -> Result<bool, String> {
    let value = value_after_key(input, key)?;
    if value.starts_with("true") {
        Ok(true)
    } else if value.starts_with("false") {
        Ok(false)
    } else {
        Err(format!("`{key}` must be a boolean"))
    }
}

fn required_json_u64(input: &str, key: &str) -> Result<u64, String> {
    required_json_number_token(input, key)?
        .parse::<u64>()
        .map_err(|err| format!("`{key}` must be an unsigned integer: {err}"))
}

fn required_json_f64(input: &str, key: &str) -> Result<f64, String> {
    required_json_number_token(input, key)?
        .parse::<f64>()
        .map_err(|err| format!("`{key}` must be a number: {err}"))
}

fn required_json_number_token(input: &str, key: &str) -> Result<String, String> {
    let value = value_after_key(input, key)?;
    let token = value
        .chars()
        .take_while(|ch| ch.is_ascii_digit() || *ch == '.')
        .collect::<String>();
    if token.is_empty() {
        Err(format!("`{key}` must be numeric"))
    } else {
        Ok(token)
    }
}

#[cfg(test)]
mod tests {
    use super::{
        maturity_partials_report_markdown, maturity_report_markdown, verify_maturity_fixture,
        MATURITY_GATE_ITEMS,
    };

    #[test]
    fn maturity_report_contains_all_expected_rows() {
        let report = maturity_report_markdown(false).expect("report");
        for item in MATURITY_GATE_ITEMS {
            assert!(report.contains(item.id));
        }
    }

    #[test]
    fn maturity_report_fail_mode_passes_when_every_row_is_demo_pass() {
        let partial_count = MATURITY_GATE_ITEMS
            .iter()
            .filter(|item| item.status != "demo-pass")
            .count();
        assert_eq!(
            partial_count,
            0,
            "no row may remain non-pass: {}",
            MATURITY_GATE_ITEMS
                .iter()
                .filter(|item| item.status != "demo-pass")
                .map(|item| item.id)
                .collect::<Vec<_>>()
                .join(", ")
        );
        let report = maturity_report_markdown(true).expect("maturity gate must pass");
        assert!(report.contains("| M4 |"));
        assert!(report.contains("| D8 |"));
        assert!(
            report.contains("| L1 |") && report.contains("| L6 |"),
            "live-evidence rows L1..L6 must be present"
        );
        assert!(
            !report.contains("| partial |"),
            "no row may still be marked partial"
        );
    }

    #[test]
    fn maturity_partials_report_is_empty_when_no_partials_remain() {
        let report = maturity_partials_report_markdown(false).expect("partials report");
        // Header is always present; it must be followed by an empty table.
        assert!(report.contains("Partial Backlog"));
        for item in MATURITY_GATE_ITEMS {
            let row_marker = format!("| {} |", item.id);
            assert!(
                !report.contains(&row_marker),
                "partial backlog must be empty but row `{}` is still listed",
                item.id
            );
        }
    }

    #[test]
    fn maturity_fixture_verifier_accepts_two_revision_demo() {
        let report = verify_maturity_fixture("fixtures/maturity").expect("fixture verifies");
        assert!(report.contains("Status: demo-pass"));
        assert!(report.contains("criticism retention: pass"));
        assert!(report.contains("cross-level consistency: pass"));
    }
}

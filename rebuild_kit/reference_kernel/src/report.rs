use std::path::Path;

const ARTIFACT_ROOT: &str = "coalgebra/stig_expert_critic";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CoalgebraGateItem {
    pub id: &'static str,
    pub dimension: &'static str,
    pub status: &'static str,
    pub evidence: &'static str,
    pub test: &'static str,
}

pub const COALGEBRA_GATE_ITEMS: &[CoalgebraGateItem] = &[
    item(
        "C1",
        "State",
        "demo-pass",
        "coalgebra/stig_expert_critic/StateSchema.json; StateSnapshot.json",
        "c1_to_c3_have_state_observation_and_event_artifacts",
    ),
    item(
        "C2",
        "Observation",
        "demo-pass",
        "coalgebra/stig_expert_critic/ObservationSchema.json",
        "c1_to_c3_have_state_observation_and_event_artifacts",
    ),
    item(
        "C3",
        "Event/Input",
        "demo-pass",
        "coalgebra/stig_expert_critic/EventSchema.json",
        "c1_to_c3_have_state_observation_and_event_artifacts",
    ),
    item(
        "C4",
        "Behavior Map",
        "demo-pass",
        "src/model.rs::step",
        "c4_step_is_deterministic",
    ),
    item(
        "C5",
        "Behavioral Distinction",
        "demo-pass",
        "src/model.rs::states_are_distinguishable",
        "c5_distinguishes_behaviorally_different_states",
    ),
    item(
        "C6",
        "Falsifier",
        "demo-pass",
        "coalgebra/stig_expert_critic/FalsifierCatalog.md",
        "c6_falsifier_catalog_is_non_vacuous_and_executed",
    ),
    item(
        "C7",
        "Scope",
        "demo-pass",
        "coalgebra/stig_expert_critic/ScopeRecord.json",
        "c7_and_c8_scope_and_witness_presence_are_explicit",
    ),
    item(
        "C8",
        "Witness Presence",
        "demo-pass",
        "coalgebra/stig_expert_critic/WitnessSpec.json",
        "c7_and_c8_scope_and_witness_presence_are_explicit",
    ),
    item(
        "C9",
        "Witness Testability",
        "demo-pass",
        "coalgebra/stig_expert_critic/WitnessTestSuite.md",
        "c9_witness_testability_rejects_bad_witness_and_survives_good_one",
    ),
    item(
        "C10",
        "Break/Fix Closure",
        "demo-pass",
        "coalgebra/stig_expert_critic/BreakFixTrialRecords.jsonl; ledgers/demo/break_fix.jsonl",
        "c10_break_fix_closure_detects_break_and_revalidates_fix",
    ),
    item(
        "C11",
        "Synthesis Demotion",
        "demo-pass",
        "coalgebra/stig_expert_critic/SynthesizedArtifactRecords.jsonl",
        "c11_synthesized_artifact_is_rejected_after_failed_witness_attack",
    ),
    item(
        "C12",
        "Failure Preservation",
        "demo-pass",
        "coalgebra/stig_expert_critic/RawEvidenceManifest.json; blobstore/demo",
        "c12_verifier_rejects_missing_or_tampered_evidence_blob",
    ),
    item(
        "C13",
        "Advisory-Only Remediation",
        "demo-pass",
        "coalgebra/stig_expert_critic/RemediationAdviceRecord.json",
        "c13_remediation_is_advisory_and_requires_post_fix_evidence",
    ),
    item(
        "C14",
        "Deterministic Replay",
        "demo-pass",
        "src/ledger.rs; ledgers/demo/*.jsonl",
        "c14_replay_is_deterministic_and_offline_verifiable",
    ),
    item(
        "C15",
        "Promotion Gate",
        "demo-pass",
        "coalgebra/stig_expert_critic/PromotionPolicy.md; PromotionRecord.json",
        "c15_promotion_policy_refuses_insufficient_survivor_lineage",
    ),
    item(
        "C16",
        "Criticism Durability",
        "demo-pass",
        "coalgebra/stig_expert_critic/CriticismLedger.jsonl",
        "c16_ledger_rejects_removed_or_overwritten_failure_records",
    ),
    item(
        "C17",
        "Optimization Guardrail",
        "demo-pass",
        "coalgebra/stig_expert_critic/WHRReport.md",
        "c17_optimization_guardrail_rejects_visibility_or_falsifier_loss",
    ),
    item(
        "C18",
        "No Direct Alignment",
        "demo-pass",
        "src/model.rs::run_field_equality_pullback",
        "c18_direct_alignment_bypass_is_rejected",
    ),
    item(
        "C19",
        "Multi-Level Consistency",
        "demo-pass",
        "coalgebra/stig_expert_critic/ContradictionRecords.jsonl",
        "c19_contradiction_detection_records_claim_witness_evidence_mismatch",
    ),
    item(
        "C20",
        "Governance Consistency",
        "demo-pass",
        "coalgebra/stig_expert_critic/Governance.md",
        "c20_governance_requires_machine_policy_and_human_signoff",
    ),
];

const fn item(
    id: &'static str,
    dimension: &'static str,
    status: &'static str,
    evidence: &'static str,
    test: &'static str,
) -> CoalgebraGateItem {
    CoalgebraGateItem {
        id,
        dimension,
        status,
        evidence,
        test,
    }
}

pub fn coalgebra_report_markdown(fail_on_missing_core: bool) -> Result<String, String> {
    let mut missing = Vec::new();
    for item in COALGEBRA_GATE_ITEMS {
        for artifact in item.evidence.split(';').map(str::trim) {
            if artifact.starts_with("src/")
                || artifact.starts_with("ledgers/")
                || artifact == "blobstore/demo"
            {
                continue;
            }
            let path = if artifact.starts_with("coalgebra/") {
                artifact.to_string()
            } else {
                format!("{ARTIFACT_ROOT}/{artifact}")
            };
            if !Path::new(&path).exists() {
                missing.push(format!("{} missing artifact {}", item.id, artifact));
            }
        }
    }

    if fail_on_missing_core && missing.iter().any(|entry| is_core_missing(entry)) {
        return Err(missing.join("\n"));
    }

    let mut output = String::new();
    output.push_str("# Coalgebra Gate Report\n\n");
    output.push_str("Subject: STIG Expert Critic P0a\n\n");
    output.push_str("Status: demo-pass, not production-promotable\n\n");
    output.push_str("| ID | Dimension | Status | Evidence | Test |\n");
    output.push_str("| --- | --- | --- | --- | --- |\n");
    for item in COALGEBRA_GATE_ITEMS {
        output.push_str(&format!(
            "| {} | {} | {} | `{}` | `{}` |\n",
            item.id, item.dimension, item.status, item.evidence, item.test
        ));
    }
    if !missing.is_empty() {
        output.push_str("\n## Missing Artifacts\n\n");
        for entry in missing {
            output.push_str(&format!("- {entry}\n"));
        }
    }
    Ok(output)
}

fn is_core_missing(entry: &str) -> bool {
    matches!(
        &entry[..2],
        "C1" | "C2" | "C3" | "C4" | "C5" | "C6" | "C7" | "C8" | "C9"
    )
}

#[cfg(test)]
mod tests {
    use super::coalgebra_report_markdown;

    #[test]
    fn report_contains_all_gate_ids() {
        let report = coalgebra_report_markdown(true).expect("report");
        for index in 1..=20 {
            assert!(report.contains(&format!("C{index}")));
        }
    }
}

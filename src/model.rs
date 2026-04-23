#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FieldEqualityWitness {
    pub witness_id: String,
    pub observable_field: String,
    pub expected_literal: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ClaimRecord {
    pub record_id: String,
    pub control_id: String,
    pub expected_value: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceRecord {
    pub record_id: String,
    pub field_name: String,
    pub observed_value: String,
    pub blob_path: String,
    pub blob_sha256: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FalsifierRecord {
    pub record_id: String,
    pub family: String,
    pub counterexample_field: String,
    pub counterexample_value: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PullbackRecord {
    pub record_id: String,
    pub claim_id: String,
    pub evidence_id: String,
    pub witness_id: String,
    pub judgment_state: String,
    pub falsifier_ids: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BreakFixTrialRecord {
    pub record_id: String,
    pub trial_id: String,
    pub control_id: String,
    pub baseline_evidence_id: String,
    pub break_evidence_id: String,
    pub post_fix_evidence_id: String,
    pub break_detected: bool,
    pub fix_revalidated: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RemediationAdviceRecord {
    pub record_id: String,
    pub advice_id: String,
    pub control_id: String,
    pub advisory_only: bool,
    pub post_fix_evidence_id: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PromotionDecisionRecord {
    pub record_id: String,
    pub subject: String,
    pub decision: String,
    pub reason: String,
    pub survived_trials: u64,
    pub required_trials: u64,
    pub human_signoff_present: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WitnessAdequacyRecord {
    pub record_id: String,
    pub witness_id: String,
    pub status: String,
    pub criticism: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SynthesizedArtifactRecord {
    pub record_id: String,
    pub artifact_id: String,
    pub artifact_kind: String,
    pub status: String,
    pub promotion_allowed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OptimizationGuardrailRecord {
    pub record_id: String,
    pub optimization_id: String,
    pub falsifier_yield_preserved: bool,
    pub evidence_visibility_preserved: bool,
    pub failure_visibility_preserved: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContradictionRecord {
    pub record_id: String,
    pub claim_id: String,
    pub witness_id: String,
    pub evidence_id: String,
    pub contradiction_kind: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GovernanceDecisionRecord {
    pub record_id: String,
    pub subject: String,
    pub machine_policy_present: bool,
    pub human_signoff_present: bool,
    pub decision: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ControlDispositionRecord {
    pub record_id: String,
    pub control_id: String,
    pub disposition: String,
    pub rationale: String,
    pub evidence_blob_paths: Vec<String>,
    pub evidence_blob_sha256s: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BatchRecord {
    pub record_id: String,
    pub batch_id: String,
    pub committed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeRecord {
    pub record_id: String,
    pub platform: String,
    pub tmos_version: String,
    pub module: String,
    pub topology: String,
    pub credential_scope: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CoalgebraState {
    pub state_id: String,
    pub witness: FieldEqualityWitness,
    pub scope: ScopeRecord,
    pub survivor_rule: String,
    pub open_criticisms: Vec<String>,
    pub trust_state: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CoalgebraEvent {
    RunPullback {
        claim: ClaimRecord,
        evidence: EvidenceRecord,
        falsifiers: Vec<FalsifierRecord>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StepResult {
    pub next_state: CoalgebraState,
    pub observations: Vec<Record>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Record {
    Scope(ScopeRecord),
    Claim(ClaimRecord),
    Evidence(EvidenceRecord),
    Witness(FieldEqualityWitness),
    Falsifier(FalsifierRecord),
    Pullback(PullbackRecord),
    BreakFixTrial(BreakFixTrialRecord),
    RemediationAdvice(RemediationAdviceRecord),
    PromotionDecision(PromotionDecisionRecord),
    WitnessAdequacy(WitnessAdequacyRecord),
    SynthesizedArtifact(SynthesizedArtifactRecord),
    OptimizationGuardrail(OptimizationGuardrailRecord),
    Contradiction(ContradictionRecord),
    GovernanceDecision(GovernanceDecisionRecord),
    ControlDisposition(ControlDispositionRecord),
    Batch(BatchRecord),
}

pub fn run_field_equality_pullback(
    claim: &ClaimRecord,
    evidence: &EvidenceRecord,
    witness: &FieldEqualityWitness,
    falsifiers: &[FalsifierRecord],
) -> Result<PullbackRecord, String> {
    if claim.control_id != witness.witness_id {
        return Err("claim control_id must match witness_id".to_string());
    }
    if claim.expected_value != witness.expected_literal {
        return Err("claim expected value must match witness expected literal".to_string());
    }
    if evidence.field_name != witness.observable_field {
        return Err("evidence field must match witness observable field".to_string());
    }
    if evidence.observed_value != witness.expected_literal {
        return Err("FieldEquality comparison failed".to_string());
    }
    if !falsifiers.iter().any(FalsifierRecord::is_non_vacuous) {
        return Err("PASS_WITH_FALSIFIER requires a non-vacuous falsifier".to_string());
    }

    Ok(PullbackRecord {
        record_id: "pullback-1".to_string(),
        claim_id: claim.record_id.clone(),
        evidence_id: evidence.record_id.clone(),
        witness_id: witness.witness_id.clone(),
        judgment_state: "PASS_WITH_FALSIFIER".to_string(),
        falsifier_ids: falsifiers
            .iter()
            .filter(|falsifier| falsifier.is_non_vacuous())
            .map(|falsifier| falsifier.record_id.clone())
            .collect(),
    })
}

pub fn detect_field_equality_break(
    evidence: &EvidenceRecord,
    witness: &FieldEqualityWitness,
) -> bool {
    evidence.field_name == witness.observable_field
        && evidence.observed_value != witness.expected_literal
}

pub fn validate_remediation_advice(
    advice: &RemediationAdviceRecord,
    post_fix_evidence: &EvidenceRecord,
    witness: &FieldEqualityWitness,
) -> Result<(), String> {
    if !advice.advisory_only {
        return Err("remediation advice must be advisory_only".to_string());
    }
    if advice.post_fix_evidence_id != post_fix_evidence.record_id {
        return Err("remediation advice must cite fresh post-fix evidence".to_string());
    }
    if post_fix_evidence.observed_value != witness.expected_literal {
        return Err("post-fix evidence does not revalidate the witness".to_string());
    }
    Ok(())
}

pub fn evaluate_promotion(
    subject: &str,
    survived_trials: u64,
    required_trials: u64,
    human_signoff_present: bool,
) -> PromotionDecisionRecord {
    let promoted = survived_trials >= required_trials && human_signoff_present;
    PromotionDecisionRecord {
        record_id: "promotion-decision-1".to_string(),
        subject: subject.to_string(),
        decision: if promoted { "PROMOTED" } else { "REFUSED" }.to_string(),
        reason: if promoted {
            "required survivor lineage and human signoff present".to_string()
        } else {
            "insufficient production survivor lineage or missing human signoff".to_string()
        },
        survived_trials,
        required_trials,
        human_signoff_present,
    }
}

pub fn evaluate_witness_adequacy(
    witness: &FieldEqualityWitness,
    attack_evidence: &EvidenceRecord,
) -> WitnessAdequacyRecord {
    let hides_failure = attack_evidence.field_name == witness.observable_field
        && attack_evidence.observed_value == witness.expected_literal;
    WitnessAdequacyRecord {
        record_id: "witness-adequacy-1".to_string(),
        witness_id: witness.witness_id.clone(),
        status: if hides_failure {
            "REJECTED"
        } else {
            "SURVIVED"
        }
        .to_string(),
        criticism: if hides_failure {
            "witness hides seeded failure".to_string()
        } else {
            "witness detects seeded failure".to_string()
        },
    }
}

pub fn evaluate_synthesized_artifact(
    artifact_id: &str,
    adequacy: &WitnessAdequacyRecord,
) -> SynthesizedArtifactRecord {
    SynthesizedArtifactRecord {
        record_id: "synth-artifact-1".to_string(),
        artifact_id: artifact_id.to_string(),
        artifact_kind: "validator".to_string(),
        status: if adequacy.status == "SURVIVED" {
            "SURVIVED"
        } else {
            "REJECTED"
        }
        .to_string(),
        promotion_allowed: false,
    }
}

pub fn evaluate_optimization_guardrail(
    optimization_id: &str,
    falsifier_yield_preserved: bool,
    evidence_visibility_preserved: bool,
    failure_visibility_preserved: bool,
) -> OptimizationGuardrailRecord {
    OptimizationGuardrailRecord {
        record_id: "optimization-guardrail-1".to_string(),
        optimization_id: optimization_id.to_string(),
        falsifier_yield_preserved,
        evidence_visibility_preserved,
        failure_visibility_preserved,
    }
}

pub fn detect_contradiction(
    claim: &ClaimRecord,
    witness: &FieldEqualityWitness,
    evidence: &EvidenceRecord,
) -> Option<ContradictionRecord> {
    if claim.expected_value != witness.expected_literal
        || evidence.field_name != witness.observable_field
        || (evidence.observed_value != witness.expected_literal
            && claim.expected_value == witness.expected_literal)
    {
        Some(ContradictionRecord {
            record_id: "contradiction-1".to_string(),
            claim_id: claim.record_id.clone(),
            witness_id: witness.witness_id.clone(),
            evidence_id: evidence.record_id.clone(),
            contradiction_kind: "claim_witness_evidence_mismatch".to_string(),
        })
    } else {
        None
    }
}

pub fn evaluate_governance(
    subject: &str,
    machine_policy_present: bool,
    human_signoff_present: bool,
) -> GovernanceDecisionRecord {
    GovernanceDecisionRecord {
        record_id: "governance-1".to_string(),
        subject: subject.to_string(),
        machine_policy_present,
        human_signoff_present,
        decision: if machine_policy_present && human_signoff_present {
            "APPROVED"
        } else {
            "REFUSED"
        }
        .to_string(),
    }
}

pub fn step(state: &CoalgebraState, event: CoalgebraEvent) -> Result<StepResult, String> {
    match event {
        CoalgebraEvent::RunPullback {
            claim,
            evidence,
            falsifiers,
        } => {
            let pullback =
                run_field_equality_pullback(&claim, &evidence, &state.witness, &falsifiers)?;
            let mut observations = vec![
                Record::Scope(state.scope.clone()),
                Record::Witness(state.witness.clone()),
                Record::Claim(claim),
                Record::Evidence(evidence),
            ];
            observations.extend(falsifiers.into_iter().map(Record::Falsifier));
            observations.push(Record::Pullback(pullback));
            observations.push(Record::Batch(BatchRecord {
                record_id: "batch-1".to_string(),
                batch_id: "p0a-demo-batch".to_string(),
                committed: true,
            }));

            let mut next_state = state.clone();
            next_state.state_id = format!("{}:after-pullback", state.state_id);

            Ok(StepResult {
                next_state,
                observations,
            })
        }
    }
}

pub fn trace_for_event(state: &CoalgebraState, event: CoalgebraEvent) -> String {
    match step(state, event) {
        Ok(result) => result
            .observations
            .iter()
            .map(|record| format!("{}:{}", record.kind(), record.payload_json()))
            .collect::<Vec<_>>()
            .join("\n"),
        Err(err) => format!("ERROR:{err}"),
    }
}

pub fn states_are_distinguishable(
    left: &CoalgebraState,
    right: &CoalgebraState,
    event: CoalgebraEvent,
) -> bool {
    trace_for_event(left, event.clone()) != trace_for_event(right, event)
}

impl FalsifierRecord {
    pub fn is_non_vacuous(&self) -> bool {
        self.family == "observational"
            && !self.counterexample_field.trim().is_empty()
            && !self.counterexample_value.trim().is_empty()
    }
}

impl Record {
    pub fn kind(&self) -> &'static str {
        match self {
            Record::Scope(_) => "ScopeRecord",
            Record::Claim(_) => "ClaimRecord",
            Record::Evidence(_) => "EvidenceRecord",
            Record::Witness(_) => "WitnessRecord",
            Record::Falsifier(_) => "FalsifierRecord",
            Record::Pullback(_) => "PullbackRecord",
            Record::BreakFixTrial(_) => "BreakFixTrialRecord",
            Record::RemediationAdvice(_) => "RemediationAdviceRecord",
            Record::PromotionDecision(_) => "PromotionDecisionRecord",
            Record::WitnessAdequacy(_) => "WitnessAdequacyRecord",
            Record::SynthesizedArtifact(_) => "SynthesizedArtifactRecord",
            Record::OptimizationGuardrail(_) => "OptimizationGuardrailRecord",
            Record::Contradiction(_) => "ContradictionRecord",
            Record::GovernanceDecision(_) => "GovernanceDecisionRecord",
            Record::ControlDisposition(_) => "ControlDispositionRecord",
            Record::Batch(_) => "BatchRecord",
        }
    }

    pub fn payload_json(&self) -> String {
        match self {
            Record::Scope(record) => format!(
                "{{\"credential_scope\":\"{}\",\"module\":\"{}\",\"platform\":\"{}\",\"record_id\":\"{}\",\"tmos_version\":\"{}\",\"topology\":\"{}\"}}",
                escape_json(&record.credential_scope),
                escape_json(&record.module),
                escape_json(&record.platform),
                escape_json(&record.record_id),
                escape_json(&record.tmos_version),
                escape_json(&record.topology)
            ),
            Record::Claim(record) => format!(
                "{{\"control_id\":\"{}\",\"expected_value\":\"{}\",\"record_id\":\"{}\"}}",
                escape_json(&record.control_id),
                escape_json(&record.expected_value),
                escape_json(&record.record_id)
            ),
            Record::Evidence(record) => format!(
                "{{\"blob_path\":\"{}\",\"blob_sha256\":\"{}\",\"field_name\":\"{}\",\"observed_value\":\"{}\",\"record_id\":\"{}\"}}",
                escape_json(&record.blob_path),
                escape_json(&record.blob_sha256),
                escape_json(&record.field_name),
                escape_json(&record.observed_value),
                escape_json(&record.record_id)
            ),
            Record::Witness(record) => format!(
                "{{\"expected_literal\":\"{}\",\"family\":\"FieldEquality\",\"observable_field\":\"{}\",\"witness_id\":\"{}\"}}",
                escape_json(&record.expected_literal),
                escape_json(&record.observable_field),
                escape_json(&record.witness_id)
            ),
            Record::Falsifier(record) => format!(
                "{{\"counterexample_field\":\"{}\",\"counterexample_value\":\"{}\",\"family\":\"{}\",\"record_id\":\"{}\"}}",
                escape_json(&record.counterexample_field),
                escape_json(&record.counterexample_value),
                escape_json(&record.family),
                escape_json(&record.record_id)
            ),
            Record::Pullback(record) => {
                let falsifier_ids = record
                    .falsifier_ids
                    .iter()
                    .map(|id| format!("\"{}\"", escape_json(id)))
                    .collect::<Vec<_>>()
                    .join(",");
                format!(
                    "{{\"claim_id\":\"{}\",\"evidence_id\":\"{}\",\"falsifier_ids\":[{}],\"judgment_state\":\"{}\",\"record_id\":\"{}\",\"witness_id\":\"{}\"}}",
                    escape_json(&record.claim_id),
                    escape_json(&record.evidence_id),
                    falsifier_ids,
                    escape_json(&record.judgment_state),
                    escape_json(&record.record_id),
                    escape_json(&record.witness_id)
                )
            }
            Record::BreakFixTrial(record) => format!(
                "{{\"baseline_evidence_id\":\"{}\",\"break_detected\":{},\"break_evidence_id\":\"{}\",\"control_id\":\"{}\",\"fix_revalidated\":{},\"post_fix_evidence_id\":\"{}\",\"record_id\":\"{}\",\"trial_id\":\"{}\"}}",
                escape_json(&record.baseline_evidence_id),
                if record.break_detected { "true" } else { "false" },
                escape_json(&record.break_evidence_id),
                escape_json(&record.control_id),
                if record.fix_revalidated { "true" } else { "false" },
                escape_json(&record.post_fix_evidence_id),
                escape_json(&record.record_id),
                escape_json(&record.trial_id),
            ),
            Record::RemediationAdvice(record) => format!(
                "{{\"advice_id\":\"{}\",\"advisory_only\":{},\"control_id\":\"{}\",\"post_fix_evidence_id\":\"{}\",\"record_id\":\"{}\"}}",
                escape_json(&record.advice_id),
                if record.advisory_only { "true" } else { "false" },
                escape_json(&record.control_id),
                escape_json(&record.post_fix_evidence_id),
                escape_json(&record.record_id),
            ),
            Record::PromotionDecision(record) => format!(
                "{{\"decision\":\"{}\",\"human_signoff_present\":{},\"reason\":\"{}\",\"record_id\":\"{}\",\"required_trials\":{},\"subject\":\"{}\",\"survived_trials\":{}}}",
                escape_json(&record.decision),
                if record.human_signoff_present { "true" } else { "false" },
                escape_json(&record.reason),
                escape_json(&record.record_id),
                record.required_trials,
                escape_json(&record.subject),
                record.survived_trials,
            ),
            Record::WitnessAdequacy(record) => format!(
                "{{\"criticism\":\"{}\",\"record_id\":\"{}\",\"status\":\"{}\",\"witness_id\":\"{}\"}}",
                escape_json(&record.criticism),
                escape_json(&record.record_id),
                escape_json(&record.status),
                escape_json(&record.witness_id),
            ),
            Record::SynthesizedArtifact(record) => format!(
                "{{\"artifact_id\":\"{}\",\"artifact_kind\":\"{}\",\"promotion_allowed\":{},\"record_id\":\"{}\",\"status\":\"{}\"}}",
                escape_json(&record.artifact_id),
                escape_json(&record.artifact_kind),
                if record.promotion_allowed { "true" } else { "false" },
                escape_json(&record.record_id),
                escape_json(&record.status),
            ),
            Record::OptimizationGuardrail(record) => format!(
                "{{\"evidence_visibility_preserved\":{},\"failure_visibility_preserved\":{},\"falsifier_yield_preserved\":{},\"optimization_id\":\"{}\",\"record_id\":\"{}\"}}",
                if record.evidence_visibility_preserved { "true" } else { "false" },
                if record.failure_visibility_preserved { "true" } else { "false" },
                if record.falsifier_yield_preserved { "true" } else { "false" },
                escape_json(&record.optimization_id),
                escape_json(&record.record_id),
            ),
            Record::Contradiction(record) => format!(
                "{{\"claim_id\":\"{}\",\"contradiction_kind\":\"{}\",\"evidence_id\":\"{}\",\"record_id\":\"{}\",\"witness_id\":\"{}\"}}",
                escape_json(&record.claim_id),
                escape_json(&record.contradiction_kind),
                escape_json(&record.evidence_id),
                escape_json(&record.record_id),
                escape_json(&record.witness_id),
            ),
            Record::GovernanceDecision(record) => format!(
                "{{\"decision\":\"{}\",\"human_signoff_present\":{},\"machine_policy_present\":{},\"record_id\":\"{}\",\"subject\":\"{}\"}}",
                escape_json(&record.decision),
                if record.human_signoff_present { "true" } else { "false" },
                if record.machine_policy_present { "true" } else { "false" },
                escape_json(&record.record_id),
                escape_json(&record.subject),
            ),
            Record::ControlDisposition(record) => {
                let evidence_blob_paths = record
                    .evidence_blob_paths
                    .iter()
                    .map(|path| format!("\"{}\"", escape_json(path)))
                    .collect::<Vec<_>>()
                    .join(",");
                let evidence_blob_sha256s = record
                    .evidence_blob_sha256s
                    .iter()
                    .map(|hash| format!("\"{}\"", escape_json(hash)))
                    .collect::<Vec<_>>()
                    .join(",");
                format!(
                    "{{\"control_id\":\"{}\",\"disposition\":\"{}\",\"evidence_blob_paths\":[{}],\"evidence_blob_sha256s\":[{}],\"rationale\":\"{}\",\"record_id\":\"{}\"}}",
                    escape_json(&record.control_id),
                    escape_json(&record.disposition),
                    evidence_blob_paths,
                    evidence_blob_sha256s,
                    escape_json(&record.rationale),
                    escape_json(&record.record_id),
                )
            }
            Record::Batch(record) => format!(
                "{{\"batch_id\":\"{}\",\"committed\":{},\"record_id\":\"{}\"}}",
                escape_json(&record.batch_id),
                if record.committed { "true" } else { "false" },
                escape_json(&record.record_id)
            ),
        }
    }
}

pub fn escape_json(input: &str) -> String {
    let mut output = String::with_capacity(input.len());
    for ch in input.chars() {
        match ch {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            c => output.push(c),
        }
    }
    output
}

#[cfg(test)]
mod tests {
    use super::{
        run_field_equality_pullback, ClaimRecord, EvidenceRecord, FalsifierRecord,
        FieldEqualityWitness,
    };

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
            blob_path: "blobstore/demo/sha256/f1/995216dcfbca4efddfa35f22f1deceaa1d31ee7a829f9d6d72ed78a1aa258a".to_string(),
            blob_sha256: "f1995216dcfbca4efddfa35f22f1deceaa1d31ee7a829f9d6d72ed78a1aa258a".to_string(),
        }
    }

    fn witness() -> FieldEqualityWitness {
        FieldEqualityWitness {
            witness_id: "demo.banner.approved".to_string(),
            observable_field: "banner_text".to_string(),
            expected_literal: "APPROVED".to_string(),
        }
    }

    #[test]
    fn accepts_pass_with_non_vacuous_falsifier() {
        let falsifier = FalsifierRecord {
            record_id: "falsifier-1".to_string(),
            family: "observational".to_string(),
            counterexample_field: "banner_text".to_string(),
            counterexample_value: "DENIED".to_string(),
        };

        let pullback = run_field_equality_pullback(&claim(), &evidence(), &witness(), &[falsifier])
            .expect("valid P0a pullback");

        assert_eq!(pullback.judgment_state, "PASS_WITH_FALSIFIER");
        assert_eq!(pullback.falsifier_ids, vec!["falsifier-1"]);
    }

    #[test]
    fn rejects_pass_without_non_vacuous_falsifier() {
        let falsifier = FalsifierRecord {
            record_id: "falsifier-1".to_string(),
            family: "observational".to_string(),
            counterexample_field: String::new(),
            counterexample_value: String::new(),
        };

        let err = run_field_equality_pullback(&claim(), &evidence(), &witness(), &[falsifier])
            .expect_err("vacuous falsifier must fail");

        assert!(err.contains("non-vacuous falsifier"));
    }
}

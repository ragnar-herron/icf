use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

use crate::model::Record;

pub fn write_ledger(path: impl AsRef<Path>, records: &[Record]) -> Result<(), String> {
    if let Some(parent) = path.as_ref().parent() {
        fs::create_dir_all(parent)
            .map_err(|err| format!("failed to create {}: {err}", parent.display()))?;
    }

    let mut output = String::new();
    let mut prev_hash: Option<String> = None;
    for record in records {
        let payload = record.payload_json();
        let line = ledger_line(record.kind(), &payload, prev_hash.as_deref());
        prev_hash = Some(required_json_string(&line, "record_hash")?);
        output.push_str(&line);
        output.push('\n');
    }

    let mut file = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(path.as_ref())
        .map_err(|err| format!("failed to open {}: {err}", path.as_ref().display()))?;
    file.write_all(output.as_bytes())
        .map_err(|err| format!("failed to write {}: {err}", path.as_ref().display()))
}

pub fn verify_ledger_path(path: impl AsRef<Path>) -> Result<(), String> {
    let content = fs::read_to_string(path.as_ref())
        .map_err(|err| format!("failed to read {}: {err}", path.as_ref().display()))?;
    verify_ledger_text(&content)
}

pub fn verify_ledger_text(content: &str) -> Result<(), String> {
    let mut expected_prev: Option<String> = None;
    let mut record_ids = Vec::new();
    let mut witnesses = Vec::new();
    let mut claims = Vec::new();
    let mut evidence_records = Vec::new();
    let mut falsifier_ids = Vec::new();
    let mut non_vacuous_falsifier_ids = Vec::new();
    let mut break_fix_trials = Vec::new();
    let mut remediation_advice = Vec::new();
    let mut saw_scope = false;
    let mut saw_witness = false;
    let mut saw_claim = false;
    let mut saw_evidence = false;
    let mut saw_falsifier = false;
    let mut saw_pullback = false;
    let mut saw_control_disposition = false;
    let mut saw_committed_batch = false;

    for (index, line) in content
        .lines()
        .filter(|line| !line.trim().is_empty())
        .enumerate()
    {
        let prev_hash = optional_json_string(line, "prev_hash")?;
        if prev_hash != expected_prev {
            return Err(format!(
                "record {index}: prev_hash mismatch: expected {}, got {}",
                format_optional(expected_prev.as_deref()),
                format_optional(prev_hash.as_deref())
            ));
        }

        let kind = required_json_string(line, "kind")?;
        if saw_committed_batch {
            return Err(format!(
                "record {index}: no records may appear after committed BatchRecord"
            ));
        }

        let payload = extract_payload(line)?;
        let actual_hash = required_json_string(line, "record_hash")?;
        let expected_hash = record_hash(prev_hash.as_deref(), &kind, payload);
        if actual_hash != expected_hash {
            return Err(format!(
                "record {index}: record_hash mismatch: expected {expected_hash}, got {actual_hash}"
            ));
        }

        if kind != "WitnessRecord" {
            let record_id = required_json_string(payload, "record_id")?;
            require_unique_id(&mut record_ids, record_id, "record_id", index)?;
        }

        match kind.as_str() {
            "ScopeRecord" => {
                saw_scope = true;
            }
            "WitnessRecord" => {
                saw_witness = true;
                let witness_id = required_json_string(payload, "witness_id")?;
                require_unique_witness_id(&witnesses, &witness_id, index)?;
                witnesses.push(WitnessFacts {
                    witness_id,
                    observable_field: required_json_string(payload, "observable_field")?,
                    expected_literal: required_json_string(payload, "expected_literal")?,
                });
            }
            "ClaimRecord" => {
                saw_claim = true;
                claims.push(ClaimFacts {
                    record_id: required_json_string(payload, "record_id")?,
                    control_id: required_json_string(payload, "control_id")?,
                    expected_value: required_json_string(payload, "expected_value")?,
                });
            }
            "EvidenceRecord" => {
                saw_evidence = true;
                evidence_records.push(EvidenceFacts {
                    record_id: required_json_string(payload, "record_id")?,
                    field_name: required_json_string(payload, "field_name")?,
                    observed_value: required_json_string(payload, "observed_value")?,
                });
                verify_evidence_blob(payload)?;
            }
            "FalsifierRecord" => {
                saw_falsifier = true;
                let record_id = required_json_string(payload, "record_id")?;
                falsifier_ids.push(record_id.clone());
                let family = required_json_string(payload, "family")?;
                let field = required_json_string(payload, "counterexample_field")?;
                let value = required_json_string(payload, "counterexample_value")?;
                if family == "observational" && !field.trim().is_empty() && !value.trim().is_empty()
                {
                    non_vacuous_falsifier_ids.push(record_id);
                }
            }
            "PullbackRecord" => {
                if !saw_scope || !saw_witness || !saw_claim || !saw_evidence {
                    return Err(format!(
                        "record {index}: PullbackRecord requires prior scope, witness, claim, and evidence records"
                    ));
                }
                saw_pullback = true;
                let claim_id = required_json_string(payload, "claim_id")?;
                let evidence_id = required_json_string(payload, "evidence_id")?;
                let witness_id = required_json_string(payload, "witness_id")?;
                let cited_falsifier_ids = required_json_string_array(payload, "falsifier_ids")?;
                let claim = find_claim(&claims, &claim_id).ok_or_else(|| {
                    format!("record {index}: PullbackRecord cites unknown claim_id {claim_id}")
                })?;
                let evidence = find_evidence(&evidence_records, &evidence_id).ok_or_else(|| {
                    format!(
                        "record {index}: PullbackRecord cites unknown evidence_id {evidence_id}"
                    )
                })?;
                let witness = find_witness(&witnesses, &witness_id).ok_or_else(|| {
                    format!("record {index}: PullbackRecord cites unknown witness_id {witness_id}")
                })?;
                for falsifier_id in &cited_falsifier_ids {
                    if !falsifier_ids.contains(falsifier_id) {
                        return Err(format!(
                            "record {index}: PullbackRecord cites unknown falsifier_id {falsifier_id}"
                        ));
                    }
                }
                let state = required_json_string(payload, "judgment_state")?;
                verify_field_equality_pullback_semantics(index, &state, claim, evidence, witness)?;
                if state == "PASS_WITH_FALSIFIER"
                    && !cited_falsifier_ids
                        .iter()
                        .any(|id| non_vacuous_falsifier_ids.contains(id))
                {
                    return Err(format!(
                        "record {index}: PASS_WITH_FALSIFIER requires a cited non-vacuous falsifier"
                    ));
                }
            }
            "BatchRecord" => {
                saw_committed_batch = required_json_bool(payload, "committed")?;
            }
            "BreakFixTrialRecord" => {
                break_fix_trials.push(BreakFixTrialFacts {
                    index,
                    baseline_evidence_id: required_json_string(payload, "baseline_evidence_id")?,
                    break_evidence_id: required_json_string(payload, "break_evidence_id")?,
                    post_fix_evidence_id: required_json_string(payload, "post_fix_evidence_id")?,
                    break_detected: required_json_bool(payload, "break_detected")?,
                    fix_revalidated: required_json_bool(payload, "fix_revalidated")?,
                });
            }
            "RemediationAdviceRecord" => {
                remediation_advice.push(RemediationAdviceFacts {
                    index,
                    advisory_only: required_json_bool(payload, "advisory_only")?,
                    post_fix_evidence_id: required_json_string(payload, "post_fix_evidence_id")?,
                });
            }
            "PromotionDecisionRecord" => {
                verify_promotion_decision(
                    index,
                    required_json_u64(payload, "survived_trials")?,
                    required_json_u64(payload, "required_trials")?,
                    required_json_bool(payload, "human_signoff_present")?,
                    &required_json_string(payload, "decision")?,
                )?;
            }
            "GovernanceDecisionRecord" => {
                verify_governance_decision(
                    index,
                    required_json_bool(payload, "machine_policy_present")?,
                    required_json_bool(payload, "human_signoff_present")?,
                    &required_json_string(payload, "decision")?,
                )?;
            }
            "ControlDispositionRecord" => {
                saw_control_disposition = true;
                verify_control_disposition_record(index, payload)?;
            }
            "WitnessAdequacyRecord"
            | "SynthesizedArtifactRecord"
            | "OptimizationGuardrailRecord"
            | "ContradictionRecord" => {}
            _ => {
                return Err(format!("record {index}: unsupported record kind {kind}"));
            }
        }

        expected_prev = Some(actual_hash);
    }

    if !saw_scope {
        return Err("ledger contains no ScopeRecord".to_string());
    }
    if !saw_control_disposition && !saw_witness {
        return Err("ledger contains no WitnessRecord".to_string());
    }
    if !saw_control_disposition && !saw_claim {
        return Err("ledger contains no ClaimRecord".to_string());
    }
    if !saw_control_disposition && !saw_evidence {
        return Err("ledger contains no EvidenceRecord".to_string());
    }
    if !saw_control_disposition && !saw_falsifier {
        return Err("ledger contains no FalsifierRecord".to_string());
    }
    if !saw_control_disposition && !saw_pullback {
        return Err("ledger contains no PullbackRecord".to_string());
    }
    if !saw_control_disposition && !break_fix_trials.is_empty() {
        // no-op; break/fix trials are validated below for the legacy path
    }
    if !saw_committed_batch {
        return Err("ledger contains no committed BatchRecord".to_string());
    }
    if !saw_control_disposition {
        for trial in &break_fix_trials {
            verify_break_fix_trial(&evidence_records, trial)?;
        }
        for advice in &remediation_advice {
            verify_remediation_advice(&evidence_records, advice)?;
        }
    }

    Ok(())
}

struct WitnessFacts {
    witness_id: String,
    observable_field: String,
    expected_literal: String,
}

struct ClaimFacts {
    record_id: String,
    control_id: String,
    expected_value: String,
}

struct EvidenceFacts {
    record_id: String,
    field_name: String,
    observed_value: String,
}

struct BreakFixTrialFacts {
    index: usize,
    baseline_evidence_id: String,
    break_evidence_id: String,
    post_fix_evidence_id: String,
    break_detected: bool,
    fix_revalidated: bool,
}

struct RemediationAdviceFacts {
    index: usize,
    advisory_only: bool,
    post_fix_evidence_id: String,
}

fn ledger_line(kind: &str, payload: &str, prev_hash: Option<&str>) -> String {
    let hash = record_hash(prev_hash, kind, payload);
    let prev_hash_json = match prev_hash {
        Some(value) => format!("\"{}\"", value),
        None => "null".to_string(),
    };
    format!(
        "{{\"kind\":\"{}\",\"payload\":{},\"prev_hash\":{},\"record_hash\":\"{}\"}}",
        kind, payload, prev_hash_json, hash
    )
}

fn record_hash(prev_hash: Option<&str>, kind: &str, payload: &str) -> String {
    let prev_hash_text = prev_hash.unwrap_or("ROOT");
    sha256_hex(format!("{prev_hash_text}\n{kind}\n{payload}").as_bytes())
}

fn find_witness<'a>(witnesses: &'a [WitnessFacts], witness_id: &str) -> Option<&'a WitnessFacts> {
    witnesses
        .iter()
        .find(|witness| witness.witness_id == witness_id)
}

fn find_claim<'a>(claims: &'a [ClaimFacts], record_id: &str) -> Option<&'a ClaimFacts> {
    claims.iter().find(|claim| claim.record_id == record_id)
}

fn find_evidence<'a>(
    evidence_records: &'a [EvidenceFacts],
    record_id: &str,
) -> Option<&'a EvidenceFacts> {
    evidence_records
        .iter()
        .find(|evidence| evidence.record_id == record_id)
}

fn verify_field_equality_pullback_semantics(
    index: usize,
    state: &str,
    claim: &ClaimFacts,
    evidence: &EvidenceFacts,
    witness: &WitnessFacts,
) -> Result<(), String> {
    if claim.control_id != witness.witness_id {
        return Err(format!(
            "record {index}: PullbackRecord claim control_id does not match witness_id"
        ));
    }
    if claim.expected_value != witness.expected_literal {
        return Err(format!(
            "record {index}: PullbackRecord claim expected_value does not match witness expected_literal"
        ));
    }
    if evidence.field_name != witness.observable_field {
        return Err(format!(
            "record {index}: PullbackRecord evidence field_name does not match witness observable_field"
        ));
    }

    let recomputed_state = if evidence.observed_value == witness.expected_literal {
        "PASS_WITH_FALSIFIER"
    } else {
        "FAIL"
    };
    if state != recomputed_state {
        return Err(format!(
            "record {index}: PullbackRecord judgment_state mismatch: expected {recomputed_state}, got {state}"
        ));
    }

    Ok(())
}

fn verify_break_fix_trial(
    evidence_records: &[EvidenceFacts],
    trial: &BreakFixTrialFacts,
) -> Result<(), String> {
    let baseline =
        find_evidence(evidence_records, &trial.baseline_evidence_id).ok_or_else(|| {
            format!(
                "record {}: BreakFixTrialRecord cites unknown baseline_evidence_id {}",
                trial.index, trial.baseline_evidence_id
            )
        })?;
    let broken = find_evidence(evidence_records, &trial.break_evidence_id).ok_or_else(|| {
        format!(
            "record {}: BreakFixTrialRecord cites unknown break_evidence_id {}",
            trial.index, trial.break_evidence_id
        )
    })?;
    let post_fix =
        find_evidence(evidence_records, &trial.post_fix_evidence_id).ok_or_else(|| {
            format!(
                "record {}: BreakFixTrialRecord cites unknown post_fix_evidence_id {}",
                trial.index, trial.post_fix_evidence_id
            )
        })?;

    if baseline.field_name != broken.field_name || baseline.field_name != post_fix.field_name {
        return Err(format!(
            "record {}: BreakFixTrialRecord evidence fields do not match",
            trial.index
        ));
    }
    if !trial.break_detected || baseline.observed_value == broken.observed_value {
        return Err(format!(
            "record {}: BreakFixTrialRecord did not preserve a detected break",
            trial.index
        ));
    }
    if !trial.fix_revalidated || baseline.observed_value != post_fix.observed_value {
        return Err(format!(
            "record {}: BreakFixTrialRecord did not preserve a revalidated fix",
            trial.index
        ));
    }

    Ok(())
}

fn verify_remediation_advice(
    evidence_records: &[EvidenceFacts],
    advice: &RemediationAdviceFacts,
) -> Result<(), String> {
    if !advice.advisory_only {
        return Err(format!(
            "record {}: RemediationAdviceRecord must be advisory_only",
            advice.index
        ));
    }
    if find_evidence(evidence_records, &advice.post_fix_evidence_id).is_none() {
        return Err(format!(
            "record {}: RemediationAdviceRecord cites unknown post_fix_evidence_id {}",
            advice.index, advice.post_fix_evidence_id
        ));
    }

    Ok(())
}

fn verify_promotion_decision(
    index: usize,
    survived_trials: u64,
    required_trials: u64,
    human_signoff_present: bool,
    decision: &str,
) -> Result<(), String> {
    let expected = if survived_trials >= required_trials && human_signoff_present {
        "PROMOTED"
    } else {
        "REFUSED"
    };
    if decision != expected {
        return Err(format!(
            "record {index}: PromotionDecisionRecord decision mismatch: expected {expected}, got {decision}"
        ));
    }
    Ok(())
}

fn verify_governance_decision(
    index: usize,
    machine_policy_present: bool,
    human_signoff_present: bool,
    decision: &str,
) -> Result<(), String> {
    let expected = if machine_policy_present && human_signoff_present {
        "APPROVED"
    } else {
        "REFUSED"
    };
    if decision != expected {
        return Err(format!(
            "record {index}: GovernanceDecisionRecord decision mismatch: expected {expected}, got {decision}"
        ));
    }
    Ok(())
}

fn verify_evidence_blob(payload: &str) -> Result<(), String> {
    let blob_path = required_json_string(payload, "blob_path")?;
    let expected_hash = required_json_string(payload, "blob_sha256")?;
    let bytes = fs::read(&blob_path)
        .map_err(|err| format!("evidence blob missing or unreadable {blob_path}: {err}"))?;
    let actual_hash = sha256_hex(&bytes);
    if actual_hash != expected_hash {
        return Err(format!(
            "evidence blob hash mismatch for {blob_path}: expected {expected_hash}, got {actual_hash}"
        ));
    }
    Ok(())
}

fn verify_control_disposition_record(index: usize, payload: &str) -> Result<(), String> {
    let disposition = required_json_string(payload, "disposition")?;
    if !matches!(
        disposition.as_str(),
        "pass" | "fail" | "not-applicable" | "blocked-external"
    ) {
        return Err(format!(
            "record {index}: invalid ControlDispositionRecord disposition {disposition}"
        ));
    }
    let blob_paths = required_json_string_array(payload, "evidence_blob_paths")?;
    let blob_hashes = required_json_string_array(payload, "evidence_blob_sha256s")?;
    if blob_paths.is_empty() {
        return Err(format!(
            "record {index}: ControlDispositionRecord must cite at least one evidence blob"
        ));
    }
    if blob_paths.len() != blob_hashes.len() {
        return Err(format!(
            "record {index}: evidence blob path/hash count mismatch"
        ));
    }
    for (blob_path, expected_hash) in blob_paths.iter().zip(blob_hashes.iter()) {
        let bytes = fs::read(blob_path).map_err(|err| {
            format!("record {index}: evidence blob missing or unreadable {blob_path}: {err}")
        })?;
        let actual_hash = sha256_hex(&bytes);
        if actual_hash != *expected_hash {
            return Err(format!(
                "record {index}: evidence blob hash mismatch for {blob_path}: expected {expected_hash}, got {actual_hash}"
            ));
        }
    }
    Ok(())
}

fn required_json_string(input: &str, key: &str) -> Result<String, String> {
    let value = value_after_key(input, key)?;
    if !value.starts_with('"') {
        return Err(format!("{key} must be a string"));
    }
    let rest = &value[1..];
    let end = rest
        .find('"')
        .ok_or_else(|| format!("{key} string is unterminated"))?;
    Ok(rest[..end].to_string())
}

fn optional_json_string(input: &str, key: &str) -> Result<Option<String>, String> {
    let value = value_after_key(input, key)?;
    if value.starts_with("null") {
        return Ok(None);
    }
    required_json_string(input, key).map(Some)
}

fn required_json_bool(input: &str, key: &str) -> Result<bool, String> {
    let value = value_after_key(input, key)?;
    if value.starts_with("true") {
        Ok(true)
    } else if value.starts_with("false") {
        Ok(false)
    } else {
        Err(format!("{key} must be a boolean"))
    }
}

fn required_json_u64(input: &str, key: &str) -> Result<u64, String> {
    let value = value_after_key(input, key)?;
    let digits: String = value.chars().take_while(|ch| ch.is_ascii_digit()).collect();
    if digits.is_empty() {
        return Err(format!("{key} must be an unsigned integer"));
    }
    digits
        .parse()
        .map_err(|err| format!("{key} must be an unsigned integer: {err}"))
}

fn require_unique_id(
    seen: &mut Vec<String>,
    id: String,
    label: &str,
    index: usize,
) -> Result<(), String> {
    if seen.contains(&id) {
        return Err(format!("record {index}: duplicate {label} {id}"));
    }
    seen.push(id);
    Ok(())
}

fn require_unique_witness_id(
    witnesses: &[WitnessFacts],
    witness_id: &str,
    index: usize,
) -> Result<(), String> {
    if witnesses
        .iter()
        .any(|witness| witness.witness_id == witness_id)
    {
        return Err(format!("record {index}: duplicate witness_id {witness_id}"));
    }
    Ok(())
}

fn required_json_string_array(input: &str, key: &str) -> Result<Vec<String>, String> {
    let value = value_after_key(input, key)?;
    if !value.starts_with('[') {
        return Err(format!("{key} must be an array"));
    }

    let end = value
        .find(']')
        .ok_or_else(|| format!("{key} array is unterminated"))?;
    let body = value[1..end].trim();
    if body.is_empty() {
        return Ok(Vec::new());
    }

    let mut output = Vec::new();
    for raw_item in body.split(',') {
        let item = raw_item.trim();
        if !item.starts_with('"') || !item.ends_with('"') || item.len() < 2 {
            return Err(format!("{key} must contain only strings"));
        }
        output.push(item[1..item.len() - 1].to_string());
    }
    Ok(output)
}

fn value_after_key<'a>(input: &'a str, key: &str) -> Result<&'a str, String> {
    let needle = format!("\"{key}\"");
    let start = input
        .find(&needle)
        .ok_or_else(|| format!("missing key {key}"))?;
    let after_key = &input[start + needle.len()..];
    let colon = after_key
        .find(':')
        .ok_or_else(|| format!("missing ':' after {key}"))?;
    Ok(after_key[colon + 1..].trim_start())
}

fn extract_payload(line: &str) -> Result<&str, String> {
    let value = value_after_key(line, "payload")?;
    if !value.starts_with('{') {
        return Err("payload must be an object".to_string());
    }

    let mut depth = 0i32;
    let mut in_string = false;
    let mut escaped = false;
    for (index, ch) in value.char_indices() {
        if in_string {
            if escaped {
                escaped = false;
            } else if ch == '\\' {
                escaped = true;
            } else if ch == '"' {
                in_string = false;
            }
            continue;
        }

        match ch {
            '"' => in_string = true,
            '{' => depth += 1,
            '}' => {
                depth -= 1;
                if depth == 0 {
                    return Ok(&value[..=index]);
                }
            }
            _ => {}
        }
    }
    Err("payload object is unterminated".to_string())
}

fn format_optional(value: Option<&str>) -> String {
    value.unwrap_or("null").to_string()
}

pub fn sha256_hex(input: &[u8]) -> String {
    let digest = sha256(input);
    let mut output = String::with_capacity(64);
    for byte in digest {
        output.push(HEX[(byte >> 4) as usize] as char);
        output.push(HEX[(byte & 0x0f) as usize] as char);
    }
    output
}

const HEX: &[u8; 16] = b"0123456789abcdef";

const K: [u32; 64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

fn sha256(input: &[u8]) -> [u8; 32] {
    let mut h = [
        0x6a09e667u32,
        0xbb67ae85,
        0x3c6ef372,
        0xa54ff53a,
        0x510e527f,
        0x9b05688c,
        0x1f83d9ab,
        0x5be0cd19,
    ];

    let padded = pad(input);
    let mut w = [0u32; 64];
    for chunk in padded.chunks_exact(64) {
        for (i, word) in chunk.chunks_exact(4).take(16).enumerate() {
            w[i] = u32::from_be_bytes([word[0], word[1], word[2], word[3]]);
        }
        for i in 16..64 {
            let s0 = w[i - 15].rotate_right(7) ^ w[i - 15].rotate_right(18) ^ (w[i - 15] >> 3);
            let s1 = w[i - 2].rotate_right(17) ^ w[i - 2].rotate_right(19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16]
                .wrapping_add(s0)
                .wrapping_add(w[i - 7])
                .wrapping_add(s1);
        }

        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut hh) =
            (h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]);
        for i in 0..64 {
            let s1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let ch = (e & f) ^ ((!e) & g);
            let temp1 = hh
                .wrapping_add(s1)
                .wrapping_add(ch)
                .wrapping_add(K[i])
                .wrapping_add(w[i]);
            let s0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let maj = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = s0.wrapping_add(maj);

            hh = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }

        h[0] = h[0].wrapping_add(a);
        h[1] = h[1].wrapping_add(b);
        h[2] = h[2].wrapping_add(c);
        h[3] = h[3].wrapping_add(d);
        h[4] = h[4].wrapping_add(e);
        h[5] = h[5].wrapping_add(f);
        h[6] = h[6].wrapping_add(g);
        h[7] = h[7].wrapping_add(hh);
    }

    let mut out = [0u8; 32];
    for (i, word) in h.iter().enumerate() {
        out[i * 4..i * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    out
}

fn pad(input: &[u8]) -> Vec<u8> {
    let bit_len = (input.len() as u64) * 8;
    let mut padded = input.to_vec();
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    padded
}

#[cfg(test)]
mod tests {
    use super::{ledger_line, sha256_hex, verify_ledger_text};

    #[test]
    fn sha256_known_vector() {
        assert_eq!(
            sha256_hex(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        );
    }

    #[test]
    fn verifier_rejects_empty_ledger() {
        assert!(verify_ledger_text("").is_err());
    }

    #[test]
    fn verifier_rejects_unknown_record_kind() {
        let line = ledger_line("UnknownRecord", "{\"record_id\":\"unknown-1\"}", None);
        let err = verify_ledger_text(&line).expect_err("unknown kind must fail");
        assert!(err.contains("unsupported record kind UnknownRecord"));
    }
}

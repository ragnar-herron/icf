//! Gate audits for M4 (scope expansion), D1 (core pullbacks preserved),
//! D4 (stable maturation logic on a second domain),
//! D6 (metric integrity / signature + checkpoint), and
//! D8 (kernel is domain-agnostic).
//!
//! Each test is the executable equivalent of the evidence claim made by
//! `MATURITY_GATE_ITEMS` for the corresponding row. Flipping a row from
//! `partial` to `demo-pass` in `src/maturity.rs` without keeping the
//! corresponding test in this file green is a regression.

use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};

use icf::ledger::sha256_hex;
use icf::maturity::MATURITY_GATE_ITEMS;
use icf::model::{
    detect_contradiction, detect_field_equality_break, evaluate_governance,
    evaluate_optimization_guardrail, evaluate_promotion, evaluate_synthesized_artifact,
    evaluate_witness_adequacy, run_field_equality_pullback, ClaimRecord, EvidenceRecord,
    FalsifierRecord, FieldEqualityWitness,
};
use serde_json::Value;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
}

fn read_repo_text(relative: &str) -> String {
    fs::read_to_string(repo_root().join(relative))
        .unwrap_or_else(|err| panic!("failed to read {relative}: {err}"))
}

fn read_repo_bytes(relative: &str) -> Vec<u8> {
    fs::read(repo_root().join(relative))
        .unwrap_or_else(|err| panic!("failed to read {relative}: {err}"))
}

// ---------------------------------------------------------------------------
// M4 — Scope Expansion
// ---------------------------------------------------------------------------

#[test]
fn m4_scope_coverage_matrix_is_multi_axis_and_traceable() {
    let matrix = read_repo_text("coalgebra/stig_expert_critic/ScopeCoverageMatrix.json");

    assert!(
        matrix.contains("\"record_kind\": \"ScopeCoverageMatrix\""),
        "coverage matrix must declare record_kind"
    );
    assert!(
        matrix.contains("\"hidden_regressions_detected\": false"),
        "coverage expansion must not regress prior coverage"
    );

    let controls = extract_controls(&matrix);
    assert!(
        controls.len() >= 5,
        "M4 requires multi-control coverage; found only {} controls",
        controls.len()
    );

    let mut vids = BTreeSet::new();
    let mut modules = BTreeSet::new();
    let mut surfaces = BTreeSet::new();
    let mut automation = BTreeSet::new();
    let mut severities = BTreeSet::new();
    for block in &controls {
        let vid = scalar(block, "vuln_id");
        assert!(
            vid.starts_with("V-"),
            "every control must trace to a V-ID (got {vid})"
        );
        assert!(vids.insert(vid.clone()), "duplicate V-ID {vid}");
        modules.insert(scalar(block, "module"));
        surfaces.insert(scalar(block, "surface"));
        automation.insert(scalar(block, "automation_class"));
        severities.insert(scalar(block, "severity"));
    }

    assert!(
        modules.len() >= 2,
        "scope must span at least two F5 modules; got {modules:?}"
    );
    assert!(
        surfaces.len() >= 2,
        "scope must span at least two check surfaces; got {surfaces:?}"
    );
    assert!(
        automation.len() >= 2,
        "scope must span at least two automation classes; got {automation:?}"
    );
    assert!(
        severities.len() >= 2,
        "scope must span at least two severities; got {severities:?}"
    );

    // Every selected V-ID in the authoritative CSV must appear in the matrix.
    let csv = read_repo_text("docs/stig_list.csv");
    let expected: BTreeSet<String> = csv
        .lines()
        .skip(1)
        .filter_map(|line| {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed.to_string())
            }
        })
        .collect();
    assert_eq!(
        vids, expected,
        "coverage matrix must enumerate exactly the V-IDs selected in docs/stig_list.csv"
    );
}

fn extract_controls(matrix: &str) -> Vec<String> {
    let key = "\"controls\":";
    let start = matrix.find(key).expect("controls array present") + key.len();
    let rest = matrix[start..].trim_start();
    let rest = rest.strip_prefix('[').expect("controls must be an array");
    let mut depth = 0i32;
    let mut in_string = false;
    let mut escaped = false;
    let mut items: Vec<String> = Vec::new();
    let mut current = String::new();
    for ch in rest.chars() {
        if in_string {
            current.push(ch);
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
            '"' => {
                in_string = true;
                current.push(ch);
            }
            '{' => {
                depth += 1;
                current.push(ch);
            }
            '}' => {
                depth -= 1;
                current.push(ch);
                if depth == 0 {
                    items.push(current.trim().to_string());
                    current.clear();
                }
            }
            ']' if depth == 0 => return items,
            ',' if depth == 0 => current.clear(),
            _ => current.push(ch),
        }
    }
    items
}

fn scalar(block: &str, key: &str) -> String {
    let needle = format!("\"{key}\"");
    let start = block
        .find(&needle)
        .unwrap_or_else(|| panic!("key `{key}` missing from {block}"));
    let after = &block[start + needle.len()..];
    let colon = after.find(':').expect("colon after key");
    let value = after[colon + 1..].trim_start();
    if let Some(rest) = value.strip_prefix('"') {
        let end = rest.find('"').expect("string terminator");
        rest[..end].to_string()
    } else {
        value
            .chars()
            .take_while(|ch| !matches!(ch, ',' | '}' | '\n'))
            .collect::<String>()
            .trim()
            .to_string()
    }
}

// ---------------------------------------------------------------------------
// D1 — Core pullbacks preserved across revisions
// ---------------------------------------------------------------------------

#[test]
fn d1_core_pullbacks_preserved() {
    let baseline = read_repo_text("coalgebra/stig_expert_critic/PullbackBaseline.json");
    assert!(baseline.contains("\"record_kind\": \"PullbackBaseline\""));

    let required: Vec<(String, Vec<String>)> = parse_pullback_baseline(&baseline);
    assert_eq!(
        required.len(),
        10,
        "baseline must define all P1–P10 pullbacks"
    );

    for (id, keywords) in &required {
        let current = MATURITY_GATE_ITEMS
            .iter()
            .find(|item| item.id == id.as_str())
            .unwrap_or_else(|| panic!("pullback {id} missing from MATURITY_GATE_ITEMS"));
        assert_eq!(
            current.gate, "Pullback",
            "pullback {id} must remain under the Pullback gate"
        );
        assert_eq!(
            current.status, "demo-pass",
            "pullback {id} must remain demo-pass (design diff regression)"
        );

        let mut matched = 0usize;
        for keyword in keywords {
            if current.evidence.contains(keyword.as_str()) {
                matched += 1;
            }
        }
        assert!(
            matched >= 1,
            "pullback {id} current evidence `{}` must still cite at least one baseline keyword {:?}",
            current.evidence,
            keywords
        );
    }
}

fn parse_pullback_baseline(text: &str) -> Vec<(String, Vec<String>)> {
    let mut out = Vec::new();
    let mut cursor = 0usize;
    while let Some(id_idx) = text[cursor..].find("\"id\":") {
        let abs = cursor + id_idx;
        let after = &text[abs + "\"id\":".len()..];
        let quote = after.find('"').expect("id quote");
        let tail = &after[quote + 1..];
        let end = tail.find('"').expect("id end quote");
        let id = tail[..end].to_string();
        if !id.starts_with('P') {
            cursor = abs + 5;
            continue;
        }
        let kw_key = "\"required_evidence_keywords\":";
        let kw_rel = after.find(kw_key).expect("keywords key");
        let kw_after = &after[kw_rel + kw_key.len()..];
        let open = kw_after.find('[').expect("keywords open");
        let close = kw_after[open..].find(']').expect("keywords close");
        let raw = &kw_after[open + 1..open + close];
        let mut keywords = Vec::new();
        let mut rest = raw;
        while let Some(q) = rest.find('"') {
            let tail = &rest[q + 1..];
            let e = tail.find('"').expect("keyword end");
            keywords.push(tail[..e].to_string());
            rest = &tail[e + 1..];
        }
        out.push((id, keywords));
        cursor = abs + kw_rel + kw_key.len() + open + close + 1;
    }
    out
}

// ---------------------------------------------------------------------------
// D4 — Stable maturation logic on a second, non-STIG domain
// ---------------------------------------------------------------------------

#[test]
fn d4_stable_maturation_logic_on_second_domain() {
    // Domain 1: the STIG banner demo (already exercised elsewhere).
    run_maturation_logic_suite(
        "demo.banner.approved",
        "banner_text",
        "APPROVED",
        "DENIED",
        "stig_expert_critic",
    );

    // Domain 2: a synthetic NTP drift critic. The fields, values, and
    // subject are completely disjoint from the STIG domain; the kernel
    // maturation logic is applied unchanged.
    run_maturation_logic_suite(
        "demo.ntp.synchronized",
        "ntp_state",
        "synchronized",
        "drifting",
        "ntp_drift_critic_demo",
    );

    // And record-level check: the MaturationLogicStability artifact must
    // declare that the cross-domain test has actually run.
    let stability = read_repo_text("coalgebra/stig_expert_critic/MaturationLogicStability.json");
    assert!(
        stability.contains("\"cross_domain_test_status\": \"passed\""),
        "MaturationLogicStability must declare cross_domain_test_status=passed"
    );
    assert!(
        stability.contains("tests/cross_domain_maturation.rs")
            || stability.contains("tests/audit.rs"),
        "MaturationLogicStability must cite a concrete cross-domain test"
    );
}

fn run_maturation_logic_suite(
    witness_id: &str,
    field_name: &str,
    pass_literal: &str,
    fail_literal: &str,
    subject: &str,
) {
    let witness = FieldEqualityWitness {
        witness_id: witness_id.to_string(),
        observable_field: field_name.to_string(),
        expected_literal: pass_literal.to_string(),
    };
    let claim = ClaimRecord {
        record_id: "claim-x".to_string(),
        control_id: witness.witness_id.clone(),
        expected_value: pass_literal.to_string(),
    };
    let good_evidence = EvidenceRecord {
        record_id: "evidence-good".to_string(),
        field_name: field_name.to_string(),
        observed_value: pass_literal.to_string(),
        blob_path: "n/a".to_string(),
        blob_sha256: "n/a".to_string(),
    };
    let bad_evidence = EvidenceRecord {
        record_id: "evidence-bad".to_string(),
        field_name: field_name.to_string(),
        observed_value: fail_literal.to_string(),
        blob_path: "n/a".to_string(),
        blob_sha256: "n/a".to_string(),
    };
    let falsifier = FalsifierRecord {
        record_id: "falsifier-x".to_string(),
        family: "observational".to_string(),
        counterexample_field: field_name.to_string(),
        counterexample_value: fail_literal.to_string(),
    };

    // Pullback replay required (stable rule 1)
    let pullback =
        run_field_equality_pullback(&claim, &good_evidence, &witness, &[falsifier.clone()])
            .expect("pullback must succeed with good evidence and non-vacuous falsifier");
    assert_eq!(pullback.judgment_state, "PASS_WITH_FALSIFIER");

    // Non-vacuous falsifier required (stable rule 2)
    let vacuous = FalsifierRecord {
        record_id: "falsifier-vacuous".to_string(),
        family: "observational".to_string(),
        counterexample_field: String::new(),
        counterexample_value: String::new(),
    };
    assert!(run_field_equality_pullback(&claim, &good_evidence, &witness, &[vacuous]).is_err());

    // Break detection (stable rule 9)
    assert!(detect_field_equality_break(&bad_evidence, &witness));
    assert!(!detect_field_equality_break(&good_evidence, &witness));

    // Witness adequacy (stable rule 5): witness that accepts a seeded
    // pass in the failing domain is rejected.
    let seeded_false_pass = EvidenceRecord {
        record_id: "evidence-seeded".to_string(),
        field_name: field_name.to_string(),
        observed_value: pass_literal.to_string(),
        blob_path: "n/a".to_string(),
        blob_sha256: "n/a".to_string(),
    };
    let adequacy_reject = evaluate_witness_adequacy(&witness, &seeded_false_pass);
    assert_eq!(adequacy_reject.status, "REJECTED");

    let adequacy_survive = evaluate_witness_adequacy(&witness, &bad_evidence);
    assert_eq!(adequacy_survive.status, "SURVIVED");

    // Synthesis requires witness survival (stable rule 6)
    let synth_reject = evaluate_synthesized_artifact("candidate-reject", &adequacy_reject);
    assert_eq!(synth_reject.status, "REJECTED");
    let synth_survive = evaluate_synthesized_artifact("candidate-survive", &adequacy_survive);
    assert_eq!(synth_survive.status, "SURVIVED");
    assert!(
        !synth_survive.promotion_allowed,
        "synthesis must never auto-allow promotion regardless of domain"
    );

    // Optimization requires visibility preservation (stable rule 7)
    let good_opt = evaluate_optimization_guardrail("opt-ok", true, true, true);
    assert!(good_opt.falsifier_yield_preserved);
    let bad_opt = evaluate_optimization_guardrail("opt-loss", false, true, true);
    assert!(!bad_opt.falsifier_yield_preserved);

    // Contradiction detection (stable rule 8)
    assert!(detect_contradiction(&claim, &witness, &bad_evidence).is_some());
    assert!(detect_contradiction(&claim, &witness, &good_evidence).is_none());

    // Promotion + governance (stable rules 3 and 4)
    let refused = evaluate_promotion(subject, 1, 2, false);
    assert_eq!(refused.decision, "REFUSED");
    let refused_signoff_missing = evaluate_promotion(subject, 2, 2, false);
    assert_eq!(refused_signoff_missing.decision, "REFUSED");
    let promoted = evaluate_promotion(subject, 2, 2, true);
    assert_eq!(promoted.decision, "PROMOTED");

    let governance_refused = evaluate_governance(subject, true, false);
    assert_eq!(governance_refused.decision, "REFUSED");
    let governance_approved = evaluate_governance(subject, true, true);
    assert_eq!(governance_approved.decision, "APPROVED");
}

// ---------------------------------------------------------------------------
// D6 — Metric integrity via signature + checkpoint
// ---------------------------------------------------------------------------

#[test]
fn d6_metrics_match_signed_digest_and_checkpoint() {
    let signature = read_repo_text("coalgebra/stig_expert_critic/MetricSignature.json");
    assert!(signature.contains("\"record_kind\": \"MetricSignature\""));

    let files = parse_signature_files(&signature);
    assert!(
        files.len() >= 5,
        "metric signature must cover at least 5 files, got {}",
        files.len()
    );

    let mut transcript = String::new();
    for (rel, expected_hash) in &files {
        let data = read_repo_bytes(rel);
        let actual = sha256_hex(&data);
        assert_eq!(
            &actual, expected_hash,
            "metric file `{rel}` hash mismatch: expected {expected_hash}, got {actual}"
        );
        transcript.push_str(rel);
        transcript.push('\t');
        transcript.push_str(&actual);
        transcript.push('\n');
    }

    let digest_of_digests = sha256_hex(transcript.as_bytes());
    let declared_dod = find_scalar(&signature, "digest_of_digests");
    assert_eq!(
        digest_of_digests, declared_dod,
        "signature digest_of_digests does not match recomputed value"
    );

    // External anchor: CheckpointRecord must point back to the same digest.
    let checkpoint = read_repo_text("ledgers/demo/metric_checkpoint.jsonl");
    assert!(
        checkpoint.contains("\"record_kind\":\"CheckpointRecord\"")
            || checkpoint.contains("\"record_kind\": \"CheckpointRecord\""),
        "checkpoint must declare record_kind=CheckpointRecord"
    );
    let anchor_dod = find_scalar(&checkpoint, "digest_of_digests");
    assert_eq!(
        anchor_dod, digest_of_digests,
        "CheckpointRecord digest_of_digests disagrees with MetricSignature"
    );
}

fn parse_signature_files(text: &str) -> Vec<(String, String)> {
    let key = "\"files\":";
    let start = text.find(key).expect("files array present") + key.len();
    let rest = text[start..].trim_start();
    let rest = rest.strip_prefix('[').expect("files is an array");
    let close = rest.find(']').expect("files array terminator");
    let body = &rest[..close];
    let mut out = Vec::new();
    let mut cursor = 0usize;
    while let Some(open) = body[cursor..].find('{') {
        let abs_open = cursor + open;
        let tail = &body[abs_open..];
        let close_rel = tail.find('}').expect("file entry close");
        let entry = &tail[..=close_rel];
        let path = entry_value(entry, "path");
        let hash = entry_value(entry, "sha256");
        out.push((path, hash));
        cursor = abs_open + close_rel + 1;
    }
    out
}

fn entry_value(entry: &str, key: &str) -> String {
    let needle = format!("\"{key}\":");
    let idx = entry
        .find(&needle)
        .unwrap_or_else(|| panic!("key {key} missing from {entry}"));
    let after = &entry[idx + needle.len()..];
    let q = after.find('"').expect("value quote");
    let tail = &after[q + 1..];
    let end = tail.find('"').expect("value end quote");
    tail[..end].to_string()
}

fn find_scalar(text: &str, key: &str) -> String {
    let needle = format!("\"{key}\":");
    let idx = text
        .find(&needle)
        .unwrap_or_else(|| panic!("key {key} missing"));
    let after = &text[idx + needle.len()..];
    let q = after.find('"').expect("scalar quote");
    let tail = &after[q + 1..];
    let end = tail.find('"').expect("scalar end quote");
    tail[..end].to_string()
}

// ---------------------------------------------------------------------------
// D8 — Kernel is domain-agnostic (general/specialized separation)
// ---------------------------------------------------------------------------

#[test]
fn stig_pullbacks_are_anchored_to_disa_source_records() {
    let catalog_text = read_repo_text("coalgebra/stig_expert_critic/ControlCatalog.json");
    let catalog: Value = serde_json::from_str(&catalog_text).expect("catalog json");
    assert_eq!(
        catalog["source_json"], "docs/disa_stigs.json",
        "generated catalog must declare docs/disa_stigs.json as its source"
    );

    let controls = catalog["controls"].as_array().expect("controls array");
    assert!(
        !controls.is_empty(),
        "catalog must contain generated controls"
    );
    for control in controls {
        let vid = control["vuln_id"].as_str().expect("vuln_id");
        let source = &control["source_stig"];
        assert_eq!(
            source["vuln_id"], vid,
            "{vid}: source_stig must cite same V-ID"
        );
        for key in [
            "ruleID",
            "checkid",
            "fixid",
            "checktext",
            "fixtext",
            "source_sha256",
        ] {
            assert!(
                source[key].as_str().is_some_and(|value| !value.is_empty()),
                "{vid}: source_stig.{key} must be populated"
            );
        }
    }

    for vid in ["V-266084", "V-266150"] {
        let control = controls
            .iter()
            .find(|item| item["vuln_id"] == vid)
            .unwrap_or_else(|| panic!("{vid} must be in catalog"));
        assert_eq!(
            control["handler_family"], "ltm_virtual_services",
            "{vid}: virtual-server service controls must not be routed through SSL/FIPS predicates"
        );
        let source = &control["source_stig"];
        let check = source["checktext"]
            .as_str()
            .expect("checktext")
            .to_lowercase();
        let fix = source["fixtext"].as_str().expect("fixtext").to_lowercase();
        assert!(
            check.contains("virtual servers"),
            "{vid}: DISA check must drive the witness"
        );
        assert!(
            fix.contains("ppsm"),
            "{vid}: DISA fix must preserve PPSM/SSP dependency"
        );
        assert_eq!(
            control["evidence_required"][0], "virtual_server_services_restricted",
            "{vid}: generated catalog must carry executable assertion evidence"
        );
        assert_eq!(
            control["criteria"]["not_a_finding"], "virtual_server_services_restricted == true",
            "{vid}: generated catalog must carry assertion criteria"
        );
        assert_eq!(
            control["tmsh_commands"][0], "tmsh list ltm virtual",
            "{vid}: generated catalog must carry assertion validation command"
        );
        let ports = control["organization_policy"]["disallowed_destination_ports"]
            .as_array()
            .unwrap_or_else(|| panic!("{vid}: disallowed ports must be an array"));
        for port in [23, 80, 445, 3389] {
            assert!(
                ports.iter().any(|value| value.as_i64() == Some(port)),
                "{vid}: organization policy must include disallowed port {port}"
            );
        }
    }
}

#[test]
fn d8_kernel_is_domain_agnostic() {
    let forbidden = ["F5", "BIG-IP", "TMOS", "stig_expert_critic", "stig", "STIG"];
    let kernels = ["src/model.rs", "src/ledger.rs"];

    for kernel in kernels {
        let content = read_repo_text(kernel);
        let prod = production_region(&content);
        for token in forbidden {
            assert!(
                !prod.contains(token),
                "{kernel}: kernel production code must not reference domain-specific token `{token}`. \
                 Move STIG-specific logic into an adapter module (e.g. src/demo.rs)."
            );
        }
    }

    // Prove STIG-specific identifiers DO live in the adapter, not because
    // adapters are required to repeat a string, but because the present
    // adapter is the STIG demo. This is a sanity check: if someone ever
    // factored the STIG strings OUT of the adapter and into the kernel,
    // the kernel scan would fail, but we also want a positive anchor that
    // the adapter is the place those strings belong.
    let adapter = read_repo_text("src/demo.rs");
    for token in ["F5 BIG-IP", "banner_text"] {
        assert!(
            adapter.contains(token),
            "STIG-specific demo adapter must continue to own token `{token}`"
        );
    }
}

fn production_region(source: &str) -> &str {
    match source.find("#[cfg(test)]") {
        Some(idx) => &source[..idx],
        None => source,
    }
}

// ---------------------------------------------------------------------------
// Sanity: these audits must be independent of path state.
// ---------------------------------------------------------------------------

#[test]
fn audits_run_from_repo_root_only() {
    let cwd = std::env::current_dir().expect("cwd");
    let root = repo_root();
    assert!(
        Path::new(&root).join("Cargo.toml").exists(),
        "CARGO_MANIFEST_DIR ({}) must contain Cargo.toml so audits can locate artifacts",
        root.display()
    );
    // Touch cwd to avoid an unused warning; do not assert anything about it.
    let _ = cwd;
}

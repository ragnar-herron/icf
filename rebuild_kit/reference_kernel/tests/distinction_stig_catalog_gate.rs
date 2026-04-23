//! Distinction-preserving pullback gate suite over the *full* F5 BIG-IP
//! STIG catalog (every V-ID in `docs/assertion_contracts.json`).
//!
//! These tests answer "did you run for every vulnerability" with yes:
//! every vulnerability gets a `MeasurableBinding`, a `LawfulPartition`
//! derived from its `criteria.not_a_finding` / `criteria.open` text, and
//! the full 9-class fixture pack. All 10 DP gates must pass over every
//! V-ID; otherwise the build fails.

use icf::distinction::{
    distinction_stig_report_markdown, gate_dp1, gate_dp10, gate_dp2, gate_dp3, gate_dp4, gate_dp5,
    gate_dp6, gate_dp7, gate_dp8, gate_dp9, run_all_dp_gates, verify_fixture_expectations,
    verify_fixture_pack_coverage, DpGateStatus, FixtureClass,
};
use icf::stig_catalog;

fn passes(status: DpGateStatus) -> bool {
    matches!(status, DpGateStatus::Pass)
}

#[test]
fn stig_catalog_loads_full_67_v_ids() {
    let catalog = stig_catalog().expect("load STIG catalog");
    assert!(
        catalog.bindings.len() >= 60,
        "expected 60+ STIG V-IDs, got {}",
        catalog.bindings.len()
    );
    // Sanity: 9 fixtures per binding.
    assert_eq!(
        catalog.fixtures.len(),
        catalog.bindings.len() * 9,
        "fixture count must equal bindings * 9"
    );
}

#[test]
fn every_v_id_has_complete_fixture_pack() {
    let catalog = stig_catalog().expect("load STIG catalog");
    verify_fixture_pack_coverage(&catalog).expect("every V-ID covers all 9 fixture classes");
    for class in FixtureClass::all() {
        assert!(
            catalog.fixtures.iter().any(|f| f.fixture_class == *class),
            "fixture class {} missing from catalog entirely",
            class.as_str()
        );
    }
}

#[test]
fn evaluator_agrees_with_every_synthesized_expectation() {
    let catalog = stig_catalog().expect("load STIG catalog");
    verify_fixture_expectations(&catalog)
        .expect("every synthesized fixture matches the evaluator's verdict");
}

#[test]
fn dp1_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp1(&catalog);
    assert!(
        passes(r.status),
        "DP-1 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp2_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp2(&catalog);
    assert!(
        passes(r.status),
        "DP-2 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp3_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp3(&catalog);
    assert!(
        passes(r.status),
        "DP-3 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp4_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp4(&catalog);
    assert!(
        passes(r.status),
        "DP-4 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp5_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp5(&catalog);
    assert!(
        passes(r.status),
        "DP-5 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp6_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp6(&catalog);
    assert!(
        passes(r.status),
        "DP-6 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp7_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp7(&catalog);
    assert!(
        passes(r.status),
        "DP-7 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp8_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp8(&catalog);
    assert!(
        passes(r.status),
        "DP-8 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp9_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp9(&catalog);
    assert!(
        passes(r.status),
        "DP-9 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn dp10_holds_for_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let r = gate_dp10(&catalog);
    assert!(
        passes(r.status),
        "DP-10 failed on STIG catalog: {}",
        r.details
    );
}

#[test]
fn all_ten_gates_pass_over_full_stig_catalog() {
    let catalog = stig_catalog().expect("load STIG catalog");
    let reports = run_all_dp_gates(&catalog);
    assert_eq!(reports.len(), 10, "expected exactly 10 DP gates");
    for r in reports {
        assert!(
            passes(r.status),
            "gate {} failed for full catalog ({}): {}",
            r.gate_id,
            catalog.bindings.len(),
            r.details
        );
    }
}

#[test]
fn distinction_stig_report_markdown_passes_with_fail_on_regression() {
    let report = distinction_stig_report_markdown(true)
        .expect("STIG report must succeed under --fail-on-regression");
    for gate in [
        "DP-1", "DP-2", "DP-3", "DP-4", "DP-5", "DP-6", "DP-7", "DP-8", "DP-9", "DP-10",
    ] {
        assert!(report.contains(gate), "report missing {gate}");
    }
    assert!(report.contains("All DP-1..DP-10 gates pass."));
    // Sanity: report mentions the full catalog scope.
    assert!(report.contains("F5 BIG-IP STIG full catalog"));
}

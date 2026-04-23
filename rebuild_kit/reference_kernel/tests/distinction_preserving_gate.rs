//! Distinction-preserving pullback gate suite (DP-1 .. DP-10).
//!
//! One test per gate, each falsifiable by flipping the corresponding
//! property. The suite also covers the fixture-pack coverage contract and
//! the factory/export equivalence requirement.

use icf::distinction::{
    demo_catalog, distinction_report_markdown, evaluate_fixture, gate_dp1, gate_dp10, gate_dp2,
    gate_dp3, gate_dp4, gate_dp5, gate_dp6, gate_dp7, gate_dp8, gate_dp9, run_all_dp_gates,
    run_export_rows, run_factory_rows, verify_fixture_expectations, verify_fixture_pack_coverage,
    AtomicValueType, DistinctionCatalog, DpGateStatus, FixtureClass, FixtureExpectation,
    MeasurableBinding, RawEvidence, Verdict,
};

fn passes(status: DpGateStatus) -> bool {
    matches!(status, DpGateStatus::Pass)
}

fn fixture<'a>(catalog: &'a DistinctionCatalog, id: &str) -> &'a FixtureExpectation {
    catalog
        .fixtures
        .iter()
        .find(|f| f.fixture_id == id)
        .unwrap_or_else(|| panic!("fixture {id} not found"))
}

#[test]
fn dp1_measurable_identity_gate_passes_on_demo_catalog() {
    let catalog = demo_catalog();
    let report = gate_dp1(&catalog);
    assert!(passes(report.status), "DP-1 failed: {}", report.details);
}

#[test]
fn dp1_proxy_field_is_refused_even_when_value_matches() {
    let catalog = demo_catalog();
    let fx = fixture(&catalog, "fx.banner.proxy_only");
    let row = evaluate_fixture(&catalog, fx).expect("evaluate proxy");
    assert!(
        matches!(row.verdict, Verdict::Unresolved),
        "proxy field must not produce PASS; got {:?}",
        row.verdict
    );
}

#[test]
fn dp2_atomic_pullback_gate_rejects_noisy_surface() {
    let catalog = demo_catalog();
    let report = gate_dp2(&catalog);
    assert!(passes(report.status), "DP-2 failed: {}", report.details);

    // Every observed_atomic is a scalar token, never a list or blob marker.
    for row in run_factory_rows(&catalog).expect("rows") {
        assert!(
            !row.observed_atomic.contains("blob:"),
            "row {} leaked a blob reference: {}",
            row.row_id,
            row.observed_atomic
        );
    }
}

#[test]
fn dp3_lawful_distinction_gate_separates_disabled_from_compliant() {
    let catalog = demo_catalog();
    let report = gate_dp3(&catalog);
    assert!(passes(report.status), "DP-3 failed: {}", report.details);

    let disabled = fixture(&catalog, "fx.ssh.disabled_state");
    let boundary = fixture(&catalog, "fx.ssh.boundary_value");
    let disabled_row = evaluate_fixture(&catalog, disabled).unwrap();
    let boundary_row = evaluate_fixture(&catalog, boundary).unwrap();

    // Disabled (0) and compliant (300) must produce *distinct* verdicts.
    assert_ne!(
        disabled_row.verdict, boundary_row.verdict,
        "0 and 300 must not collapse into the same verdict class"
    );
    assert!(matches!(disabled_row.verdict, Verdict::Fail));
    assert!(matches!(boundary_row.verdict, Verdict::Pass));
}

#[test]
fn dp4_representation_equivalence_class_collapses_bad_encodings_identically() {
    let catalog = demo_catalog();
    let report = gate_dp4(&catalog);
    assert!(passes(report.status), "DP-4 failed: {}", report.details);

    let ids = [
        "fx.fw.bad_canonical",
        "fx.fw.bad_representation_variant_zero",
        "fx.fw.bad_representation_variant_any",
        "fx.fw.bad_representation_variant_dotzero",
        "fx.fw.disabled_state",
    ];
    let mut seen = std::collections::HashSet::new();
    for id in ids {
        let row = evaluate_fixture(&catalog, fixture(&catalog, id)).unwrap();
        assert!(matches!(row.verdict, Verdict::Fail), "{id} must FAIL");
        seen.insert(row.observed_atomic.clone());
    }
    assert_eq!(
        seen.len(),
        1,
        "equivalent encodings must canonicalize to one atomic, got {seen:?}"
    );
}

#[test]
fn dp5_every_measurable_has_a_failing_bad_canonical_fixture() {
    let catalog = demo_catalog();
    let report = gate_dp5(&catalog);
    assert!(passes(report.status), "DP-5 failed: {}", report.details);
}

#[test]
fn dp6_every_measurable_has_a_passing_good_minimal_fixture() {
    let catalog = demo_catalog();
    let report = gate_dp6(&catalog);
    assert!(passes(report.status), "DP-6 failed: {}", report.details);
}

#[test]
fn dp7_factory_and_export_produce_identical_pullback_rows() {
    let catalog = demo_catalog();
    let report = gate_dp7(&catalog);
    assert!(passes(report.status), "DP-7 failed: {}", report.details);

    let factory = run_factory_rows(&catalog).expect("factory rows");
    let export = run_export_rows(&catalog).expect("export rows");
    assert_eq!(factory.len(), export.len(), "row count divergence");
    for (lhs, rhs) in factory.iter().zip(export.iter()) {
        assert_eq!(lhs.canonical_line(), rhs.canonical_line());
    }
}

#[test]
fn dp8_out_of_scope_evidence_is_unresolved_for_every_measurable() {
    let catalog = demo_catalog();
    let report = gate_dp8(&catalog);
    assert!(passes(report.status), "DP-8 failed: {}", report.details);
}

#[test]
fn dp9_every_binding_and_fixture_cites_source_stig_text() {
    let catalog = demo_catalog();
    let report = gate_dp9(&catalog);
    assert!(passes(report.status), "DP-9 failed: {}", report.details);
}

#[test]
fn dp10_ambiguous_missing_or_malformed_evidence_is_unresolved() {
    let catalog = demo_catalog();
    let report = gate_dp10(&catalog);
    assert!(passes(report.status), "DP-10 failed: {}", report.details);
}

#[test]
fn fixture_pack_coverage_is_required_and_satisfied() {
    let catalog = demo_catalog();
    verify_fixture_pack_coverage(&catalog).expect("demo catalog covers required fixture classes");
    for class in FixtureClass::all() {
        if matches!(
            class,
            FixtureClass::BadRepresentationVariant | FixtureClass::BoundaryValue
        ) {
            // These classes are only required where structurally meaningful;
            // the firewall and ssh measurables exercise them.
            let any = catalog.fixtures.iter().any(|f| f.fixture_class == *class);
            assert!(any, "fixture class {} missing entirely", class.as_str());
        }
    }
}

#[test]
fn evaluator_agrees_with_every_declared_fixture_expectation() {
    let catalog = demo_catalog();
    verify_fixture_expectations(&catalog).expect("evaluator matches every expectation");
}

#[test]
fn distinction_report_markdown_lists_all_ten_gates() {
    let report = distinction_report_markdown(true).expect("report with all gates passing");
    for gate in [
        "DP-1", "DP-2", "DP-3", "DP-4", "DP-5", "DP-6", "DP-7", "DP-8", "DP-9", "DP-10",
    ] {
        assert!(report.contains(gate), "report missing {gate}");
    }
    assert!(report.contains("All DP-1..DP-10 gates pass."));
}

#[test]
fn run_all_dp_gates_enumerates_exactly_ten_gates() {
    let catalog = demo_catalog();
    let reports = run_all_dp_gates(&catalog);
    assert_eq!(reports.len(), 10);
    let ids: Vec<_> = reports.iter().map(|r| r.gate_id).collect();
    assert_eq!(
        ids,
        vec!["DP-1", "DP-2", "DP-3", "DP-4", "DP-5", "DP-6", "DP-7", "DP-8", "DP-9", "DP-10",]
    );
    for r in reports {
        assert!(
            passes(r.status),
            "gate {} did not pass: {}",
            r.gate_id,
            r.details
        );
    }
}

/// Negative test: if the catalog is mutated so that DP-1 identity is
/// violated (two bindings pointing to the same runtime source in the same
/// scope), the gate must fail. This is the falsifier that DP-1 demands.
#[test]
fn dp1_falsifies_when_two_bindings_share_one_runtime_source() {
    let mut catalog = demo_catalog();
    // DP-1 falsifier per spec: same scope + same runtime source but
    // *different* lawful interpretation. We point the clash binding to the
    // SSH integer partition while keeping the banner field, so the same
    // field is claimed under conflicting partitions.
    let clash = MeasurableBinding {
        contract_measurable_id: "demo.banner.shadow".to_string(),
        runtime_source_paths: vec!["banner_text".to_string()],
        projection_fn_id: "select_banner_text".to_string(),
        atomic_value_type: AtomicValueType::Integer,
        lawful_partition_id: "partition.ssh.idle_timeout".to_string(),
        representation_equivalence_class_ids: Vec::new(),
        scope_id: "f5-bigip:ltm:standalone:fixture".to_string(),
        source_stig_clause: "shadow".to_string(),
        adapter_interpretation_note: "shadow".to_string(),
        lawful_partition_rationale: "shadow".to_string(),
        required_atomic_description: "shadow".to_string(),
        org_defined_value: None,
    };
    catalog.bindings.push(clash);
    let report = gate_dp1(&catalog);
    assert!(
        matches!(report.status, DpGateStatus::Fail),
        "DP-1 must falsify duplicate runtime_source_path"
    );
}

/// Negative test: flipping the lawful-partition interpretation (making
/// 0 = pass under "<= 300") must trigger DP-3 failure. This is the
/// falsifier that DP-3 demands.
#[test]
fn dp3_falsifies_when_disabled_collapses_into_pass_band() {
    let mut catalog = demo_catalog();
    let partition = catalog
        .partitions
        .iter_mut()
        .find(|p| p.partition_id == "partition.ssh.idle_timeout")
        .expect("partition present");
    partition.fail_predicates.retain(|p| {
        !matches!(
            p,
            icf::distinction::PartitionPredicate::IntEqualsSentinel(0)
        )
    });
    partition.pass_predicates =
        vec![icf::distinction::PartitionPredicate::IntClosedRange { lo: 0, hi: 300 }];
    let report = gate_dp3(&catalog);
    assert!(
        matches!(report.status, DpGateStatus::Fail),
        "DP-3 must falsify when disabled collapses into pass band"
    );
}

/// Negative test: DP-10 must fail if absent evidence silently becomes a
/// pass. We construct a pathological fixture pack where the evaluator is
/// fed a Field with the compliant token and the expectation is mislabelled
/// `AbsentState`; DP-10 should still fail because the fixture class
/// `AbsentState` no longer reaches UNRESOLVED.
#[test]
fn dp10_falsifies_when_absent_state_resolves_to_pass() {
    let mut catalog = demo_catalog();
    let target = catalog
        .fixtures
        .iter_mut()
        .find(|f| f.fixture_id == "fx.banner.absent_state")
        .expect("fixture present");
    target.raw_evidence = RawEvidence::Field {
        field: "banner_text".to_string(),
        value: "APPROVED".to_string(),
    };
    let report = gate_dp10(&catalog);
    assert!(
        matches!(report.status, DpGateStatus::Fail),
        "DP-10 must falsify when absent_state fixture produces a non-UNRESOLVED verdict"
    );
}

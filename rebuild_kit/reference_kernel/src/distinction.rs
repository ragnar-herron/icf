//! Distinction-preserving pullback gates (DP-1 .. DP-10).
//!
//! Implements the record types, fixture pack semantics, and evaluator that
//! `docs/distinction_preserving_test.md` demands. The evaluator is pure:
//! given a `MeasurableBinding`, a `LawfulPartition`, a representation
//! equivalence catalog, and a fixture, it emits exactly one
//! `AtomicPullbackRow` with a closed `Verdict`.
//!
//! v0.2 of this module adds the set-valued-measurable escape clause: a
//! binding may declare multiple `runtime_source_paths`. The contract is then
//! an *explicitly* set-valued measurable (DP-2 allows this), and predicates
//! become multi-term (`AllOf` / `AnyOf` of `(field, op, value)` terms), which
//! is what the F5 STIG `criteria.not_a_finding` / `criteria.open` catalog
//! uses.

use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum AtomicValueType {
    Token,
    Integer,
    Bool,
    /// Explicitly set-valued measurable: projection returns a tuple over
    /// the declared runtime source paths.
    Tuple,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum Verdict {
    Pass,
    Fail,
    Unresolved,
}

impl Verdict {
    pub fn as_str(&self) -> &'static str {
        match self {
            Verdict::Pass => "PASS",
            Verdict::Fail => "FAIL",
            Verdict::Unresolved => "UNRESOLVED",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
pub enum CmpOp {
    Eq,
    Ne,
    Le,
    Ge,
    Lt,
    Gt,
}

impl CmpOp {
    pub fn as_str(&self) -> &'static str {
        match self {
            CmpOp::Eq => "==",
            CmpOp::Ne => "!=",
            CmpOp::Le => "<=",
            CmpOp::Ge => ">=",
            CmpOp::Lt => "<",
            CmpOp::Gt => ">",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum TermValue {
    Int(i64),
    Bool(bool),
    Token(String),
    /// Reference to a scope-derived per-binding value (kept symbolic so the
    /// evaluator can compare against the declared reference).
    OrgDefined,
}

impl TermValue {
    pub fn as_canonical(&self) -> String {
        match self {
            TermValue::Int(i) => i.to_string(),
            TermValue::Bool(b) => b.to_string(),
            TermValue::Token(s) => s.clone(),
            TermValue::OrgDefined => "<org_defined_value>".to_string(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct Term {
    pub field: String,
    pub op: CmpOp,
    pub value: TermValue,
}

impl Term {
    pub fn as_canonical(&self) -> String {
        format!(
            "{} {} {}",
            self.field,
            self.op.as_str(),
            self.value.as_canonical()
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum PartitionPredicate {
    /// Single-field / single-value predicate: observed token equals this.
    EqualsToken(String),
    /// Integer in closed range (single-field).
    IntClosedRange { lo: i64, hi: i64 },
    /// Integer equal to a sentinel (single-field).
    IntEqualsSentinel(i64),
    /// Token in set (single-field).
    InSet(Vec<String>),
    /// Token not in set (single-field).
    NotInSet(Vec<String>),
    /// Token equals a disabled literal (single-field).
    EqualsDisabled(String),
    /// Every term must match (AND of terms).
    AllOf(Vec<Term>),
    /// At least one term must match (OR of terms).
    AnyOf(Vec<Term>),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct MeasurableBinding {
    /// DP-1: the exact contract measurable being bound.
    pub contract_measurable_id: String,
    /// DP-1: declared runtime source paths. Single element for scalar
    /// measurables; multi-element only when the contract explicitly
    /// defines a set-valued measurable.
    pub runtime_source_paths: Vec<String>,
    /// DP-1: declared projection function identifier.
    pub projection_fn_id: String,
    /// DP-1: declared atomic value type.
    pub atomic_value_type: AtomicValueType,
    /// DP-3: the lawful partition that governs pass/fail/unresolved classes.
    pub lawful_partition_id: String,
    /// DP-4: equivalence classes that map variant encodings onto the same
    /// canonical atomic.
    pub representation_equivalence_class_ids: Vec<String>,
    /// DP-8: declared scope for this measurable. Out-of-scope evidence is
    /// unresolved, never a silent pass.
    pub scope_id: String,
    /// DP-9: STIG clause cited by the measurable.
    pub source_stig_clause: String,
    /// DP-9: adapter interpretation note -- no invented semantics.
    pub adapter_interpretation_note: String,
    /// DP-9: rationale for the lawful partition choice.
    pub lawful_partition_rationale: String,
    /// Human-readable form of the required atomic (printed on the pullback row).
    pub required_atomic_description: String,
    /// Optional concrete value for `org_defined_value` references (symbolic
    /// value used only when a predicate term references `OrgDefined`).
    pub org_defined_value: Option<TermValue>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LawfulPartition {
    pub partition_id: String,
    pub measurable_id: String,
    pub pass_predicates: Vec<PartitionPredicate>,
    pub fail_predicates: Vec<PartitionPredicate>,
    pub comparison_operator: String,
    pub rationale: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct RepresentationEquivalenceClass {
    pub class_id: String,
    pub measurable_id: String,
    pub canonical_encoding: String,
    pub equivalent_encodings: Vec<String>,
    pub normalization_rule: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize)]
pub enum FixtureClass {
    GoodMinimal,
    BadCanonical,
    BadRepresentationVariant,
    BoundaryValue,
    DisabledState,
    AbsentState,
    MalformedState,
    NoisyEvidence,
    OutOfScopeVariant,
}

impl FixtureClass {
    pub fn as_str(&self) -> &'static str {
        match self {
            FixtureClass::GoodMinimal => "good_minimal",
            FixtureClass::BadCanonical => "bad_canonical",
            FixtureClass::BadRepresentationVariant => "bad_representation_variant",
            FixtureClass::BoundaryValue => "boundary_value",
            FixtureClass::DisabledState => "disabled_state",
            FixtureClass::AbsentState => "absent_state",
            FixtureClass::MalformedState => "malformed_state",
            FixtureClass::NoisyEvidence => "noisy_evidence",
            FixtureClass::OutOfScopeVariant => "out_of_scope_variant",
        }
    }

    pub fn all() -> &'static [FixtureClass] {
        &[
            FixtureClass::GoodMinimal,
            FixtureClass::BadCanonical,
            FixtureClass::BadRepresentationVariant,
            FixtureClass::BoundaryValue,
            FixtureClass::DisabledState,
            FixtureClass::AbsentState,
            FixtureClass::MalformedState,
            FixtureClass::NoisyEvidence,
            FixtureClass::OutOfScopeVariant,
        ]
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum RawEvidence {
    /// A single (field, value) measurement.
    Field { field: String, value: String },
    /// Multi-field evidence for an explicitly set-valued measurable.
    MultiField { fields: BTreeMap<String, String> },
    /// A noisy payload: includes the target measurement plus distractor
    /// fields that must not survive projection (DP-1 / DP-2).
    NoisyField {
        target: (String, String),
        distractors: Vec<(String, String)>,
    },
    /// Multi-field noisy payload: declared fields are present, distractors
    /// ignored.
    NoisyMultiField {
        target_fields: BTreeMap<String, String>,
        distractors: Vec<(String, String)>,
    },
    /// No observation -- DP-10.
    Missing,
    /// Malformed payload that cannot be parsed into the declared atomic
    /// type -- DP-10.
    Malformed { field: String, raw: String },
    /// Evidence attached to a scope the measurable did not promote to --
    /// DP-8.
    OutOfScope {
        field: String,
        value: String,
        observed_scope_id: String,
    },
    OutOfScopeMultiField {
        fields: BTreeMap<String, String>,
        observed_scope_id: String,
    },
    /// Proxy field measurement: evidence names a *different* runtime field
    /// than the one the binding declared. DP-1 falsifier.
    ProxyField {
        proxy_field: String,
        proxy_value: String,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct FixtureExpectation {
    pub fixture_id: String,
    pub fixture_class: FixtureClass,
    pub measurable_id: String,
    pub raw_evidence: RawEvidence,
    pub expected_verdict: Verdict,
    pub source_stig_clause: String,
    pub scope_id: String,
    pub notes: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct AtomicPullbackRow {
    pub row_id: String,
    pub measurable_id: String,
    pub required_atomic: String,
    pub observed_atomic: String,
    pub comparison_operator: String,
    pub verdict: Verdict,
    pub unresolved_reason: Option<String>,
}

impl AtomicPullbackRow {
    pub fn canonical_line(&self) -> String {
        format!(
            "row_id={}|measurable_id={}|required_atomic={}|observed_atomic={}|comparison_operator={}|verdict={}|unresolved_reason={}",
            self.row_id,
            self.measurable_id,
            self.required_atomic,
            self.observed_atomic,
            self.comparison_operator,
            self.verdict.as_str(),
            self.unresolved_reason.as_deref().unwrap_or("")
        )
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Default, Serialize)]
pub struct DistinctionCatalog {
    pub bindings: Vec<MeasurableBinding>,
    pub partitions: Vec<LawfulPartition>,
    pub equivalence_classes: Vec<RepresentationEquivalenceClass>,
    pub fixtures: Vec<FixtureExpectation>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum CaptureSourceKind {
    Tmsh,
    Rest,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct CaptureSource {
    pub source_id: String,
    pub kind: CaptureSourceKind,
    pub locator: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct ExtractionRule {
    pub field: String,
    pub source_ids: Vec<String>,
    pub aliases: Vec<String>,
    pub json_pointer_candidates: Vec<String>,
    pub tmsh_property_candidates: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LiveCaptureRecipe {
    pub measurable_id: String,
    pub runtime_family: String,
    pub projection_kind: String,
    pub sources: Vec<CaptureSource>,
    pub extraction_rules: Vec<ExtractionRule>,
}

#[derive(Debug, Clone, PartialEq, Eq, Deserialize)]
pub struct LiveEvaluationRequest {
    pub measurable_id: String,
    #[serde(default)]
    pub field_map: BTreeMap<String, String>,
    #[serde(default)]
    pub raw_evidence: Option<RawEvidence>,
    #[serde(default)]
    pub observed_scope_id: Option<String>,
    #[serde(default)]
    pub evidence_source: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LiveEvaluationRow {
    #[serde(rename = "measurableId")]
    pub measurable_id: String,
    #[serde(rename = "requiredAtomic")]
    pub required_atomic: String,
    #[serde(rename = "observedAtomic")]
    pub observed_atomic: Option<String>,
    pub operator: String,
    pub verdict: String,
    #[serde(rename = "evidenceSource")]
    pub evidence_source: String,
    #[serde(rename = "comparisonExpression")]
    pub comparison_expression: String,
    #[serde(rename = "partitionClass")]
    pub partition_class: String,
    #[serde(rename = "unresolvedReason")]
    pub unresolved_reason: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct LiveEvaluationResponse {
    pub kind: String,
    pub measurable_id: String,
    pub status: String,
    pub row: LiveEvaluationRow,
}

impl DistinctionCatalog {
    pub fn binding(&self, measurable_id: &str) -> Option<&MeasurableBinding> {
        self.bindings
            .iter()
            .find(|b| b.contract_measurable_id == measurable_id)
    }

    pub fn partition(&self, partition_id: &str) -> Option<&LawfulPartition> {
        self.partitions
            .iter()
            .find(|p| p.partition_id == partition_id)
    }

    pub fn equivalence(&self, class_id: &str) -> Option<&RepresentationEquivalenceClass> {
        self.equivalence_classes
            .iter()
            .find(|e| e.class_id == class_id)
    }
}

// --------------------------------------------------------------------------
// Evaluator
// --------------------------------------------------------------------------

enum Projection {
    Scalar(String),
    Tuple(BTreeMap<String, String>),
}

enum ProjectionOutcome {
    Hit(Projection),
    Missing(String),
    Malformed(String),
}

pub fn evaluate_fixture(
    catalog: &DistinctionCatalog,
    fixture: &FixtureExpectation,
) -> Result<AtomicPullbackRow, String> {
    let binding = catalog
        .binding(&fixture.measurable_id)
        .ok_or_else(|| format!("no binding for {}", fixture.measurable_id))?;
    let partition = catalog
        .partition(&binding.lawful_partition_id)
        .ok_or_else(|| format!("no partition for {}", binding.lawful_partition_id))?;

    let row_id = format!("dp-row::{}", fixture.fixture_id);

    // DP-8: out-of-scope evidence never passes regardless of value.
    let out_of_scope_reason = match &fixture.raw_evidence {
        RawEvidence::OutOfScope {
            observed_scope_id, ..
        } if observed_scope_id != &binding.scope_id => Some(observed_scope_id.clone()),
        RawEvidence::OutOfScopeMultiField {
            observed_scope_id, ..
        } if observed_scope_id != &binding.scope_id => Some(observed_scope_id.clone()),
        _ => None,
    };
    if let Some(scope) = out_of_scope_reason {
        return Ok(AtomicPullbackRow {
            row_id,
            measurable_id: fixture.measurable_id.clone(),
            required_atomic: binding.required_atomic_description.clone(),
            observed_atomic: format!("<out_of_scope:{}>", scope),
            comparison_operator: partition.comparison_operator.clone(),
            verdict: Verdict::Unresolved,
            unresolved_reason: Some("evidence outside declared promotion scope".to_string()),
        });
    }

    let projected = project(binding, &fixture.raw_evidence);

    let (observed_atomic_str, field_map) = match projected {
        ProjectionOutcome::Hit(Projection::Scalar(value)) => {
            let mut map = BTreeMap::new();
            if let Some(field) = binding.runtime_source_paths.first() {
                map.insert(field.clone(), value.clone());
            }
            let canonical = canonicalize_scalar(binding, catalog, &value);
            (canonical, map)
        }
        ProjectionOutcome::Hit(Projection::Tuple(map)) => {
            let mut canon_map = BTreeMap::new();
            for (field, value) in &map {
                canon_map.insert(field.clone(), value.clone());
            }
            let serialized = serialize_tuple(&canon_map);
            (serialized, canon_map)
        }
        ProjectionOutcome::Missing(reason) => {
            return Ok(AtomicPullbackRow {
                row_id,
                measurable_id: fixture.measurable_id.clone(),
                required_atomic: binding.required_atomic_description.clone(),
                observed_atomic: "<absent>".to_string(),
                comparison_operator: partition.comparison_operator.clone(),
                verdict: Verdict::Unresolved,
                unresolved_reason: Some(reason),
            });
        }
        ProjectionOutcome::Malformed(reason) => {
            return Ok(AtomicPullbackRow {
                row_id,
                measurable_id: fixture.measurable_id.clone(),
                required_atomic: binding.required_atomic_description.clone(),
                observed_atomic: "<malformed>".to_string(),
                comparison_operator: partition.comparison_operator.clone(),
                verdict: Verdict::Unresolved,
                unresolved_reason: Some(reason),
            });
        }
    };

    // Parse scalar atomics into their declared atomic type.
    let parsed_int = match binding.atomic_value_type {
        AtomicValueType::Integer => match observed_atomic_str.parse::<i64>() {
            Ok(v) => Some(v),
            Err(_) => {
                return Ok(AtomicPullbackRow {
                    row_id,
                    measurable_id: fixture.measurable_id.clone(),
                    required_atomic: binding.required_atomic_description.clone(),
                    observed_atomic: observed_atomic_str,
                    comparison_operator: partition.comparison_operator.clone(),
                    verdict: Verdict::Unresolved,
                    unresolved_reason: Some(
                        "observed value does not parse as Integer atomic".to_string(),
                    ),
                });
            }
        },
        _ => None,
    };

    // DP-3: fail predicates dominate pass predicates.
    let mut verdict = Verdict::Unresolved;
    let mut unresolved_reason: Option<String> =
        Some("no lawful partition predicate matched".to_string());

    for predicate in &partition.fail_predicates {
        if predicate_matches(
            predicate,
            &observed_atomic_str,
            parsed_int,
            &field_map,
            binding,
        ) {
            verdict = Verdict::Fail;
            unresolved_reason = None;
            break;
        }
    }
    if matches!(verdict, Verdict::Unresolved) {
        for predicate in &partition.pass_predicates {
            if predicate_matches(
                predicate,
                &observed_atomic_str,
                parsed_int,
                &field_map,
                binding,
            ) {
                verdict = Verdict::Pass;
                unresolved_reason = None;
                break;
            }
        }
    }

    Ok(AtomicPullbackRow {
        row_id,
        measurable_id: fixture.measurable_id.clone(),
        required_atomic: binding.required_atomic_description.clone(),
        observed_atomic: observed_atomic_str,
        comparison_operator: partition.comparison_operator.clone(),
        verdict,
        unresolved_reason,
    })
}

fn project(binding: &MeasurableBinding, evidence: &RawEvidence) -> ProjectionOutcome {
    let declared: Vec<&String> = binding.runtime_source_paths.iter().collect();
    let is_multi =
        declared.len() > 1 || matches!(binding.atomic_value_type, AtomicValueType::Tuple);

    match evidence {
        RawEvidence::Field { field, value } => {
            if declared.len() == 1 && field == declared[0] {
                ProjectionOutcome::Hit(Projection::Scalar(value.clone()))
            } else if is_multi {
                ProjectionOutcome::Missing(format!(
                    "set-valued measurable requires all declared fields; got only `{field}`"
                ))
            } else {
                ProjectionOutcome::Missing(format!(
                    "evidence field `{}` is not the declared runtime source `{}`",
                    field,
                    declared.first().map(|s| s.as_str()).unwrap_or("")
                ))
            }
        }
        RawEvidence::MultiField { fields } => {
            let mut projected = BTreeMap::new();
            for source in &declared {
                let Some(value) = fields.get(*source) else {
                    return ProjectionOutcome::Missing(format!(
                        "multi-field evidence is missing declared runtime source `{source}`"
                    ));
                };
                projected.insert((*source).clone(), value.clone());
            }
            if is_multi {
                ProjectionOutcome::Hit(Projection::Tuple(projected))
            } else {
                let only = projected.into_values().next().unwrap_or_default();
                ProjectionOutcome::Hit(Projection::Scalar(only))
            }
        }
        RawEvidence::NoisyField {
            target,
            distractors,
        } => {
            let _ = distractors;
            if declared.len() == 1 && target.0 == *declared[0] {
                ProjectionOutcome::Hit(Projection::Scalar(target.1.clone()))
            } else {
                ProjectionOutcome::Missing(format!(
                    "noisy evidence does not contain declared runtime source `{}`",
                    declared.first().map(|s| s.as_str()).unwrap_or("")
                ))
            }
        }
        RawEvidence::NoisyMultiField {
            target_fields,
            distractors,
        } => {
            let _ = distractors;
            let mut projected = BTreeMap::new();
            for source in &declared {
                let Some(value) = target_fields.get(*source) else {
                    return ProjectionOutcome::Missing(format!(
                        "noisy multi-field evidence is missing `{source}`"
                    ));
                };
                projected.insert((*source).clone(), value.clone());
            }
            if is_multi {
                ProjectionOutcome::Hit(Projection::Tuple(projected))
            } else {
                let only = projected.into_values().next().unwrap_or_default();
                ProjectionOutcome::Hit(Projection::Scalar(only))
            }
        }
        RawEvidence::Missing => ProjectionOutcome::Missing("evidence is absent".to_string()),
        RawEvidence::Malformed { field, raw } => {
            if declared.iter().any(|d| d == &field) {
                ProjectionOutcome::Malformed(format!("evidence for `{field}` is malformed: {raw}"))
            } else {
                ProjectionOutcome::Missing(format!(
                    "malformed evidence targets `{field}`, not declared runtime source set"
                ))
            }
        }
        RawEvidence::OutOfScope { field, value, .. } => {
            if declared.len() == 1 && field == declared[0] {
                ProjectionOutcome::Hit(Projection::Scalar(value.clone()))
            } else {
                ProjectionOutcome::Missing(format!(
                    "out-of-scope evidence does not contain declared runtime source `{}`",
                    declared.first().map(|s| s.as_str()).unwrap_or("")
                ))
            }
        }
        RawEvidence::OutOfScopeMultiField { fields, .. } => {
            let mut projected = BTreeMap::new();
            for source in &declared {
                let Some(value) = fields.get(*source) else {
                    return ProjectionOutcome::Missing(format!(
                        "out-of-scope multi-field evidence is missing `{source}`"
                    ));
                };
                projected.insert((*source).clone(), value.clone());
            }
            ProjectionOutcome::Hit(Projection::Tuple(projected))
        }
        RawEvidence::ProxyField { proxy_field, .. } => ProjectionOutcome::Missing(format!(
            "refused proxy field `{proxy_field}`; declared runtime sources are {:?}",
            declared
        )),
    }
}

fn canonicalize_scalar(
    binding: &MeasurableBinding,
    catalog: &DistinctionCatalog,
    observed: &str,
) -> String {
    for class_id in &binding.representation_equivalence_class_ids {
        if let Some(class) = catalog.equivalence(class_id) {
            if class.equivalent_encodings.iter().any(|e| e == observed)
                || class.canonical_encoding == observed
            {
                return class.canonical_encoding.clone();
            }
        }
    }
    observed.to_string()
}

fn serialize_tuple(map: &BTreeMap<String, String>) -> String {
    let mut parts = Vec::with_capacity(map.len());
    for (k, v) in map {
        parts.push(format!("{k}={v}"));
    }
    parts.join(";")
}

fn predicate_matches(
    predicate: &PartitionPredicate,
    observed_str: &str,
    observed_int: Option<i64>,
    field_map: &BTreeMap<String, String>,
    binding: &MeasurableBinding,
) -> bool {
    match predicate {
        PartitionPredicate::EqualsToken(expected) => observed_str == expected,
        PartitionPredicate::IntClosedRange { lo, hi } => {
            matches!(observed_int, Some(v) if v >= *lo && v <= *hi)
        }
        PartitionPredicate::IntEqualsSentinel(sentinel) => {
            matches!(observed_int, Some(v) if v == *sentinel)
        }
        PartitionPredicate::InSet(values) => values.iter().any(|v| v == observed_str),
        PartitionPredicate::NotInSet(values) => values.iter().all(|v| v != observed_str),
        PartitionPredicate::EqualsDisabled(token) => observed_str == token,
        PartitionPredicate::AllOf(terms) => {
            terms.iter().all(|t| term_matches(t, field_map, binding))
        }
        PartitionPredicate::AnyOf(terms) => {
            terms.iter().any(|t| term_matches(t, field_map, binding))
        }
    }
}

fn term_matches(
    term: &Term,
    field_map: &BTreeMap<String, String>,
    binding: &MeasurableBinding,
) -> bool {
    let Some(raw) = field_map.get(&term.field) else {
        return false;
    };
    let target = match &term.value {
        TermValue::OrgDefined => {
            let Some(org) = &binding.org_defined_value else {
                return false;
            };
            org.clone()
        }
        other => other.clone(),
    };
    match (&target, term.op) {
        (TermValue::Int(expected), op) => {
            let Ok(actual) = raw.parse::<i64>() else {
                return false;
            };
            match op {
                CmpOp::Eq => actual == *expected,
                CmpOp::Ne => actual != *expected,
                CmpOp::Le => actual <= *expected,
                CmpOp::Ge => actual >= *expected,
                CmpOp::Lt => actual < *expected,
                CmpOp::Gt => actual > *expected,
            }
        }
        (TermValue::Bool(expected), op) => {
            let actual = match raw.as_str() {
                "true" => true,
                "false" => false,
                _ => return false,
            };
            match op {
                CmpOp::Eq => actual == *expected,
                CmpOp::Ne => actual != *expected,
                // Ordering on booleans is not meaningful in this DSL; refuse.
                _ => false,
            }
        }
        (TermValue::Token(expected), op) => match op {
            CmpOp::Eq => raw == expected,
            CmpOp::Ne => raw != expected,
            _ => false,
        },
        (TermValue::OrgDefined, _) => false,
    }
}

/// Simulated "export" evaluator: serialize the factory rows and re-parse.
pub fn run_export_rows(catalog: &DistinctionCatalog) -> Result<Vec<AtomicPullbackRow>, String> {
    let factory = run_factory_rows(catalog)?;
    let serialized: Vec<String> = factory
        .iter()
        .map(AtomicPullbackRow::canonical_line)
        .collect();
    let mut exported = Vec::with_capacity(serialized.len());
    for line in serialized {
        exported.push(parse_canonical_line(&line)?);
    }
    Ok(exported)
}

pub fn run_factory_rows(catalog: &DistinctionCatalog) -> Result<Vec<AtomicPullbackRow>, String> {
    let mut rows = Vec::with_capacity(catalog.fixtures.len());
    for fixture in &catalog.fixtures {
        rows.push(evaluate_fixture(catalog, fixture)?);
    }
    Ok(rows)
}

fn live_raw_evidence(
    binding: &MeasurableBinding,
    field_map: &BTreeMap<String, String>,
    observed_scope_id: Option<&str>,
) -> RawEvidence {
    if field_map.is_empty() {
        return RawEvidence::Missing;
    }
    let multi = binding.runtime_source_paths.len() > 1
        || matches!(binding.atomic_value_type, AtomicValueType::Tuple);
    if let Some(scope_id) = observed_scope_id {
        if scope_id != binding.scope_id {
            if multi {
                return RawEvidence::OutOfScopeMultiField {
                    fields: field_map.clone(),
                    observed_scope_id: scope_id.to_string(),
                };
            }
            if let Some(field) = binding.runtime_source_paths.first() {
                return RawEvidence::OutOfScope {
                    field: field.clone(),
                    value: field_map.get(field).cloned().unwrap_or_default(),
                    observed_scope_id: scope_id.to_string(),
                };
            }
        }
    }
    if multi {
        RawEvidence::MultiField {
            fields: field_map.clone(),
        }
    } else if let Some(field) = binding.runtime_source_paths.first() {
        match field_map.get(field) {
            Some(value) => RawEvidence::Field {
                field: field.clone(),
                value: value.clone(),
            },
            None => RawEvidence::Missing,
        }
    } else {
        RawEvidence::Missing
    }
}

fn partition_class_for_row(row: &AtomicPullbackRow) -> &'static str {
    match row.verdict {
        Verdict::Pass => "compliant",
        Verdict::Fail => "noncompliant",
        Verdict::Unresolved => {
            let reason = row.unresolved_reason.as_deref().unwrap_or("").to_ascii_lowercase();
            let row_id = row.row_id.to_ascii_lowercase();
            if reason.contains("outside declared promotion scope") || row.observed_atomic.contains("<out_of_scope:") {
                "indeterminate"
            } else if reason.contains("absent") || reason.contains("missing") || row_id.contains("absent") {
                "absent"
            } else if reason.contains("malformed") || row_id.contains("malformed") {
                "malformed"
            } else if reason.contains("disabled") || row_id.contains("disabled") {
                "disabled"
            } else {
                "indeterminate"
            }
        }
    }
}

fn status_for_row(row: &AtomicPullbackRow) -> &'static str {
    match row.verdict {
        Verdict::Pass => "not_a_finding",
        Verdict::Fail => "open",
        Verdict::Unresolved => "insufficient_evidence",
    }
}

pub fn evaluate_live_request(
    catalog: &DistinctionCatalog,
    request: &LiveEvaluationRequest,
) -> Result<LiveEvaluationResponse, String> {
    let binding = catalog
        .binding(&request.measurable_id)
        .ok_or_else(|| format!("no binding for {}", request.measurable_id))?;
    let raw_evidence = request.raw_evidence.clone().unwrap_or_else(|| {
        live_raw_evidence(
            binding,
            &request.field_map,
            request.observed_scope_id.as_deref(),
        )
    });
    let fixture = FixtureExpectation {
        fixture_id: format!("live::{}", request.measurable_id),
        fixture_class: FixtureClass::GoodMinimal,
        measurable_id: request.measurable_id.clone(),
        raw_evidence,
        expected_verdict: Verdict::Unresolved,
        source_stig_clause: binding.source_stig_clause.clone(),
        scope_id: binding.scope_id.clone(),
        notes: "live evaluation request".to_string(),
    };
    let row = evaluate_fixture(catalog, &fixture)?;
    Ok(LiveEvaluationResponse {
        kind: "LiveEvaluationResponse".to_string(),
        measurable_id: request.measurable_id.clone(),
        status: status_for_row(&row).to_string(),
        row: LiveEvaluationRow {
            measurable_id: row.measurable_id.clone(),
            required_atomic: row.required_atomic.clone(),
            observed_atomic: if row.observed_atomic.is_empty() {
                None
            } else {
                Some(row.observed_atomic.clone())
            },
            operator: row.comparison_operator.clone(),
            verdict: row.verdict.as_str().to_ascii_lowercase(),
            evidence_source: if request.evidence_source.is_empty() {
                "live::normalized_field_map".to_string()
            } else {
                request.evidence_source.clone()
            },
            comparison_expression: row.comparison_operator.clone(),
            partition_class: partition_class_for_row(&row).to_string(),
            unresolved_reason: row.unresolved_reason.clone(),
        },
    })
}

pub fn evaluate_live_json(request_json: &str) -> Result<String, String> {
    let request: LiveEvaluationRequest = serde_json::from_str(request_json)
        .map_err(|e| format!("failed to parse live evaluation request: {e}"))?;
    let catalog = crate::stig_catalog::stig_catalog()?;
    let response = evaluate_live_request(&catalog, &request)?;
    serde_json::to_string_pretty(&response)
        .map_err(|e| format!("failed to serialize live evaluation response: {e}"))
}

fn parse_canonical_line(line: &str) -> Result<AtomicPullbackRow, String> {
    // Accept '|' only as the top-level separator; '=' and ';' may appear
    // inside tuple serializations.
    let mut map: std::collections::HashMap<String, String> = std::collections::HashMap::new();
    for part in line.split('|') {
        let (key, value) = part
            .split_once('=')
            .ok_or_else(|| format!("malformed row part `{part}`"))?;
        map.insert(key.to_string(), value.to_string());
    }
    let verdict = match map.get("verdict").map(String::as_str).unwrap_or("") {
        "PASS" => Verdict::Pass,
        "FAIL" => Verdict::Fail,
        "UNRESOLVED" => Verdict::Unresolved,
        other => return Err(format!("unknown verdict `{other}`")),
    };
    let unresolved_reason = map
        .get("unresolved_reason")
        .cloned()
        .filter(|s| !s.is_empty());
    Ok(AtomicPullbackRow {
        row_id: map.remove("row_id").unwrap_or_default(),
        measurable_id: map.remove("measurable_id").unwrap_or_default(),
        required_atomic: map.remove("required_atomic").unwrap_or_default(),
        observed_atomic: map.remove("observed_atomic").unwrap_or_default(),
        comparison_operator: map.remove("comparison_operator").unwrap_or_default(),
        verdict,
        unresolved_reason,
    })
}

// --------------------------------------------------------------------------
// Gate suite
// --------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct DpGateReport {
    pub gate_id: &'static str,
    pub dimension: &'static str,
    pub status: DpGateStatus,
    pub details: String,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub enum DpGateStatus {
    Pass,
    Fail,
}

impl DpGateStatus {
    pub fn as_str(&self) -> &'static str {
        match self {
            DpGateStatus::Pass => "pass",
            DpGateStatus::Fail => "fail",
        }
    }
}

pub fn run_all_dp_gates(catalog: &DistinctionCatalog) -> Vec<DpGateReport> {
    vec![
        gate_dp1(catalog),
        gate_dp2(catalog),
        gate_dp3(catalog),
        gate_dp4(catalog),
        gate_dp5(catalog),
        gate_dp6(catalog),
        gate_dp7(catalog),
        gate_dp8(catalog),
        gate_dp9(catalog),
        gate_dp10(catalog),
    ]
}

fn report(
    gate_id: &'static str,
    dimension: &'static str,
    result: Result<String, String>,
) -> DpGateReport {
    match result {
        Ok(details) => DpGateReport {
            gate_id,
            dimension,
            status: DpGateStatus::Pass,
            details,
        },
        Err(details) => DpGateReport {
            gate_id,
            dimension,
            status: DpGateStatus::Fail,
            details,
        },
    }
}

pub fn gate_dp1(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-1", "Measurable identity", check_dp1(catalog))
}

fn check_dp1(catalog: &DistinctionCatalog) -> Result<String, String> {
    // Structural: every binding has a non-empty runtime source set and a
    // projection_fn. The DP-1 falsifier per spec is "same atomic decision
    // computed from two different fields" / "no two distinct contract
    // measurables collapse onto the same runtime field with *different*
    // lawful interpretations". So we forbid two bindings sharing a
    // (scope, source_set) only when their lawful partitions disagree.
    let mut seen: std::collections::HashMap<(String, Vec<String>), &MeasurableBinding> =
        std::collections::HashMap::new();
    for binding in &catalog.bindings {
        if binding.runtime_source_paths.is_empty() {
            return Err(format!(
                "binding {} has empty runtime_source_paths",
                binding.contract_measurable_id
            ));
        }
        if binding
            .runtime_source_paths
            .iter()
            .any(|s| s.trim().is_empty())
        {
            return Err(format!(
                "binding {} has empty runtime source entry",
                binding.contract_measurable_id
            ));
        }
        if binding.projection_fn_id.trim().is_empty() {
            return Err(format!(
                "binding {} missing projection_fn_id",
                binding.contract_measurable_id
            ));
        }
        let mut sorted = binding.runtime_source_paths.clone();
        sorted.sort();
        let key = (binding.scope_id.clone(), sorted);
        if let Some(existing) = seen.get(&key) {
            // Same (scope, sources): only legal if the lawful partitions
            // agree on pass/fail predicates AND the canonical atomic
            // surface (required_atomic_description, atomic type).
            let existing_part = catalog
                .partition(&existing.lawful_partition_id)
                .ok_or_else(|| {
                    format!(
                        "binding {} cites unknown partition {}",
                        existing.contract_measurable_id, existing.lawful_partition_id
                    )
                })?;
            let this_part = catalog
                .partition(&binding.lawful_partition_id)
                .ok_or_else(|| {
                    format!(
                        "binding {} cites unknown partition {}",
                        binding.contract_measurable_id, binding.lawful_partition_id
                    )
                })?;
            if existing.atomic_value_type != binding.atomic_value_type
                || existing_part.pass_predicates != this_part.pass_predicates
                || existing_part.fail_predicates != this_part.fail_predicates
            {
                return Err(format!(
                    "DP-1 falsifier: bindings {} and {} share runtime sources \
                     in scope `{}` but disagree on lawful interpretation",
                    existing.contract_measurable_id,
                    binding.contract_measurable_id,
                    binding.scope_id
                ));
            }
        } else {
            seen.insert(key, binding);
        }
        // Atomic type consistency: multi-field => Tuple.
        if binding.runtime_source_paths.len() > 1
            && !matches!(binding.atomic_value_type, AtomicValueType::Tuple)
        {
            return Err(format!(
                "binding {} has multiple runtime sources but atomic_value_type is not Tuple",
                binding.contract_measurable_id
            ));
        }
    }

    // Behavioral: if the catalog carries banner proxy/noise fixtures (demo
    // catalog), assert those specific falsifiers still behave correctly.
    if let Some(proxy) = catalog
        .fixtures
        .iter()
        .find(|f| f.fixture_id == "fx.banner.proxy_only")
    {
        let row = evaluate_fixture(catalog, proxy)?;
        if !matches!(row.verdict, Verdict::Unresolved) {
            return Err(format!(
                "proxy-only fixture leaked through as {}",
                row.verdict.as_str()
            ));
        }
    }
    if let Some(noisy) = catalog
        .fixtures
        .iter()
        .find(|f| f.fixture_id == "fx.banner.noisy_evidence")
    {
        let row = evaluate_fixture(catalog, noisy)?;
        if !matches!(row.verdict, Verdict::Pass) {
            return Err("demo noisy fixture must pass on declared runtime source".to_string());
        }
        if row.observed_atomic.contains("profile_dump") || row.observed_atomic.contains("backup") {
            return Err("distractor fields leaked into observed_atomic".to_string());
        }
    }

    // General behavioral check: every NoisyField/NoisyMultiField fixture in
    // the catalog must produce a verdict that matches its declared
    // expectation, and the observed_atomic must not mention any distractor
    // field names.
    for fx in &catalog.fixtures {
        match &fx.raw_evidence {
            RawEvidence::NoisyField { distractors, .. }
            | RawEvidence::NoisyMultiField { distractors, .. } => {
                let row = evaluate_fixture(catalog, fx)?;
                for (dfield, dvalue) in distractors {
                    if row.observed_atomic.contains(dfield.as_str())
                        || (row
                            .observed_atomic
                            .split(';')
                            .any(|part| part == format!("{dfield}={dvalue}")))
                    {
                        return Err(format!(
                            "distractor `{dfield}` leaked into fixture {} observed_atomic",
                            fx.fixture_id
                        ));
                    }
                }
            }
            _ => {}
        }
    }

    Ok(format!(
        "{} bindings; duplicate runtime sources refused; noise discarded",
        catalog.bindings.len()
    ))
}

pub fn gate_dp2(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-2", "Atomic pullback", check_dp2(catalog))
}

fn check_dp2(catalog: &DistinctionCatalog) -> Result<String, String> {
    let rows = run_factory_rows(catalog)?;
    for row in &rows {
        if row.row_id.is_empty()
            || row.measurable_id.is_empty()
            || row.required_atomic.is_empty()
            || row.comparison_operator.is_empty()
        {
            return Err(format!("row {} missing atomic field", row.row_id));
        }
        // Atomic surface: no JSON object/list markers may leak.
        if row.observed_atomic.contains('{')
            || row.observed_atomic.contains('}')
            || row.observed_atomic.contains('[')
            || row.observed_atomic.contains(']')
        {
            return Err(format!(
                "row {} observed_atomic is not atomic: {}",
                row.row_id, row.observed_atomic
            ));
        }
        // Tuple rows must cite a Tuple-typed binding.
        if row.observed_atomic.contains(';') {
            let binding = catalog
                .binding(&row.measurable_id)
                .ok_or_else(|| format!("row {} references unknown binding", row.row_id))?;
            if !matches!(binding.atomic_value_type, AtomicValueType::Tuple) {
                return Err(format!(
                    "row {} emits tuple atomic but binding is not Tuple-typed",
                    row.row_id
                ));
            }
        }
    }
    Ok(format!("{} atomic rows verified", rows.len()))
}

pub fn gate_dp3(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-3", "Lawful distinction", check_dp3(catalog))
}

fn check_dp3(catalog: &DistinctionCatalog) -> Result<String, String> {
    let non_pass_classes = [
        FixtureClass::DisabledState,
        FixtureClass::AbsentState,
        FixtureClass::MalformedState,
    ];
    let mut checked = 0usize;
    for binding in &catalog.bindings {
        for class in &non_pass_classes {
            let Some(fx) = catalog.fixtures.iter().find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == *class
            }) else {
                continue;
            };
            let row = evaluate_fixture(catalog, fx)?;
            if matches!(row.verdict, Verdict::Pass) {
                return Err(format!(
                    "{} fixture {} landed in PASS class for {}",
                    class.as_str(),
                    fx.fixture_id,
                    binding.contract_measurable_id
                ));
            }
            checked += 1;
        }
    }
    // Pair-wise distinction: for every binding, good_minimal and
    // bad_canonical must produce *different* verdict classes.
    for binding in &catalog.bindings {
        let good = catalog.fixtures.iter().find(|f| {
            f.measurable_id == binding.contract_measurable_id
                && f.fixture_class == FixtureClass::GoodMinimal
        });
        let bad = catalog.fixtures.iter().find(|f| {
            f.measurable_id == binding.contract_measurable_id
                && f.fixture_class == FixtureClass::BadCanonical
        });
        if let (Some(g), Some(b)) = (good, bad) {
            let gr = evaluate_fixture(catalog, g)?;
            let br = evaluate_fixture(catalog, b)?;
            if gr.verdict == br.verdict {
                return Err(format!(
                    "good and bad fixtures for {} collapse into {}",
                    binding.contract_measurable_id,
                    gr.verdict.as_str()
                ));
            }
        }
    }

    // Demo-specific check: idle_timeout boundary (300) must be PASS and
    // disabled (0) must be FAIL when those specific fixtures exist.
    if let (Some(d), Some(b)) = (
        catalog
            .fixtures
            .iter()
            .find(|f| f.fixture_id == "fx.ssh.disabled_state"),
        catalog
            .fixtures
            .iter()
            .find(|f| f.fixture_id == "fx.ssh.boundary_value"),
    ) {
        let dr = evaluate_fixture(catalog, d)?;
        let br = evaluate_fixture(catalog, b)?;
        if !matches!(dr.verdict, Verdict::Fail) {
            return Err("ssh idle_timeout=0 must FAIL (disabled)".to_string());
        }
        if !matches!(br.verdict, Verdict::Pass) {
            return Err("ssh idle_timeout=300 must PASS (upper boundary)".to_string());
        }
    }

    Ok(format!(
        "{} bindings, {} disabled/absent/malformed fixtures preserved fail-or-unresolved",
        catalog.bindings.len(),
        checked
    ))
}

pub fn gate_dp4(catalog: &DistinctionCatalog) -> DpGateReport {
    report(
        "DP-4",
        "Runtime representation equivalence",
        check_dp4(catalog),
    )
}

fn check_dp4(catalog: &DistinctionCatalog) -> Result<String, String> {
    // Every bad_canonical + bad_representation_variant pair (per
    // measurable) must produce the same verdict.
    let mut pairs = 0usize;
    for binding in &catalog.bindings {
        let canonical = catalog.fixtures.iter().find(|f| {
            f.measurable_id == binding.contract_measurable_id
                && f.fixture_class == FixtureClass::BadCanonical
        });
        let variant = catalog.fixtures.iter().find(|f| {
            f.measurable_id == binding.contract_measurable_id
                && f.fixture_class == FixtureClass::BadRepresentationVariant
        });
        if let (Some(c), Some(v)) = (canonical, variant) {
            let cr = evaluate_fixture(catalog, c)?;
            let vr = evaluate_fixture(catalog, v)?;
            if !(matches!(cr.verdict, Verdict::Fail) && matches!(vr.verdict, Verdict::Fail)) {
                return Err(format!(
                    "bad canonical/variant pair for {} does not fail identically (canonical={}, variant={})",
                    binding.contract_measurable_id,
                    cr.verdict.as_str(),
                    vr.verdict.as_str()
                ));
            }
            pairs += 1;
        }
    }

    // Demo-specific: firewall wildcard encodings all canonicalize to the
    // same atomic.
    let wildcard_ids = [
        "fx.fw.bad_canonical",
        "fx.fw.bad_representation_variant_zero",
        "fx.fw.bad_representation_variant_any",
        "fx.fw.bad_representation_variant_dotzero",
        "fx.fw.disabled_state",
    ];
    let mut seen = BTreeSet::new();
    let mut saw_wildcards = false;
    for id in wildcard_ids {
        if let Some(fx) = catalog.fixtures.iter().find(|f| f.fixture_id == id) {
            saw_wildcards = true;
            let row = evaluate_fixture(catalog, fx)?;
            if !matches!(row.verdict, Verdict::Fail) {
                return Err(format!("{id} must FAIL"));
            }
            seen.insert(row.observed_atomic);
        }
    }
    if saw_wildcards && seen.len() > 1 {
        return Err(format!(
            "wildcard encodings failed to canonicalize: {seen:?}"
        ));
    }

    Ok(format!(
        "{} bad canonical/variant pairs fail identically; wildcard encodings canonicalized",
        pairs
    ))
}

pub fn gate_dp5(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-5", "Known-bad mandatory failure", check_dp5(catalog))
}

fn check_dp5(catalog: &DistinctionCatalog) -> Result<String, String> {
    for binding in &catalog.bindings {
        let bad = catalog
            .fixtures
            .iter()
            .find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == FixtureClass::BadCanonical
            })
            .ok_or_else(|| {
                format!(
                    "measurable {} missing bad_canonical fixture",
                    binding.contract_measurable_id
                )
            })?;
        let row = evaluate_fixture(catalog, bad)?;
        if !matches!(row.verdict, Verdict::Fail) {
            return Err(format!(
                "bad_canonical fixture {} produced {}, required FAIL",
                bad.fixture_id,
                row.verdict.as_str()
            ));
        }
    }
    Ok(format!(
        "{} bad_canonical fixtures all fail",
        catalog.bindings.len()
    ))
}

pub fn gate_dp6(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-6", "Known-good admissible pass", check_dp6(catalog))
}

fn check_dp6(catalog: &DistinctionCatalog) -> Result<String, String> {
    for binding in &catalog.bindings {
        let good = catalog
            .fixtures
            .iter()
            .find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == FixtureClass::GoodMinimal
            })
            .ok_or_else(|| {
                format!(
                    "measurable {} missing good_minimal fixture",
                    binding.contract_measurable_id
                )
            })?;
        let row = evaluate_fixture(catalog, good)?;
        if !matches!(row.verdict, Verdict::Pass) {
            return Err(format!(
                "good_minimal fixture {} produced {}, required PASS",
                good.fixture_id,
                row.verdict.as_str()
            ));
        }
    }
    Ok(format!(
        "{} good_minimal fixtures all pass",
        catalog.bindings.len()
    ))
}

pub fn gate_dp7(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-7", "Export equivalence", check_dp7(catalog))
}

fn check_dp7(catalog: &DistinctionCatalog) -> Result<String, String> {
    let factory = run_factory_rows(catalog)?;
    let export = run_export_rows(catalog)?;
    if factory.len() != export.len() {
        return Err(format!(
            "factory produced {} rows but export produced {}",
            factory.len(),
            export.len()
        ));
    }
    for (lhs, rhs) in factory.iter().zip(export.iter()) {
        if lhs != rhs {
            return Err(format!(
                "row divergence between factory and export:\n  factory={}\n  export={}",
                lhs.canonical_line(),
                rhs.canonical_line()
            ));
        }
    }
    Ok(format!(
        "{} factory rows match export rows byte-identically",
        factory.len()
    ))
}

pub fn gate_dp8(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-8", "Scope honesty", check_dp8(catalog))
}

fn check_dp8(catalog: &DistinctionCatalog) -> Result<String, String> {
    for binding in &catalog.bindings {
        let fx = catalog
            .fixtures
            .iter()
            .find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == FixtureClass::OutOfScopeVariant
            })
            .ok_or_else(|| {
                format!(
                    "measurable {} missing out_of_scope_variant fixture",
                    binding.contract_measurable_id
                )
            })?;
        let row = evaluate_fixture(catalog, fx)?;
        if !matches!(row.verdict, Verdict::Unresolved) {
            return Err(format!(
                "out-of-scope fixture {} resolved to {}; must be UNRESOLVED",
                fx.fixture_id,
                row.verdict.as_str()
            ));
        }
    }
    Ok(format!(
        "{} out-of-scope fixtures all unresolved",
        catalog.bindings.len()
    ))
}

pub fn gate_dp9(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-9", "Source anchoring", check_dp9(catalog))
}

fn check_dp9(catalog: &DistinctionCatalog) -> Result<String, String> {
    for binding in &catalog.bindings {
        if binding.source_stig_clause.trim().is_empty() {
            return Err(format!(
                "binding {} lacks source_stig_clause",
                binding.contract_measurable_id
            ));
        }
        if binding.adapter_interpretation_note.trim().is_empty() {
            return Err(format!(
                "binding {} lacks adapter_interpretation_note",
                binding.contract_measurable_id
            ));
        }
        if binding.lawful_partition_rationale.trim().is_empty() {
            return Err(format!(
                "binding {} lacks lawful_partition_rationale",
                binding.contract_measurable_id
            ));
        }
    }
    for fx in &catalog.fixtures {
        if fx.source_stig_clause.trim().is_empty() {
            return Err(format!(
                "fixture {} lacks source_stig_clause",
                fx.fixture_id
            ));
        }
    }
    Ok(format!(
        "{} bindings and {} fixtures fully source-anchored",
        catalog.bindings.len(),
        catalog.fixtures.len()
    ))
}

pub fn gate_dp10(catalog: &DistinctionCatalog) -> DpGateReport {
    report("DP-10", "Unresolved honesty", check_dp10(catalog))
}

fn check_dp10(catalog: &DistinctionCatalog) -> Result<String, String> {
    let mut checked = 0usize;
    for binding in &catalog.bindings {
        let fx = catalog
            .fixtures
            .iter()
            .find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == FixtureClass::AbsentState
            })
            .ok_or_else(|| {
                format!(
                    "measurable {} missing absent_state fixture",
                    binding.contract_measurable_id
                )
            })?;
        let row = evaluate_fixture(catalog, fx)?;
        if !matches!(row.verdict, Verdict::Unresolved) {
            return Err(format!(
                "absent_state fixture {} resolved to {}; must be UNRESOLVED",
                fx.fixture_id,
                row.verdict.as_str()
            ));
        }
        if row.unresolved_reason.is_none() {
            return Err(format!(
                "absent_state fixture {} omitted unresolved_reason",
                fx.fixture_id
            ));
        }
        checked += 1;
    }
    for binding in &catalog.bindings {
        let fx = catalog
            .fixtures
            .iter()
            .find(|f| {
                f.measurable_id == binding.contract_measurable_id
                    && f.fixture_class == FixtureClass::MalformedState
            })
            .ok_or_else(|| {
                format!(
                    "measurable {} missing malformed_state fixture",
                    binding.contract_measurable_id
                )
            })?;
        let row = evaluate_fixture(catalog, fx)?;
        if !matches!(row.verdict, Verdict::Unresolved) {
            return Err(format!(
                "malformed_state fixture {} resolved to {}; must be UNRESOLVED",
                fx.fixture_id,
                row.verdict.as_str()
            ));
        }
        checked += 1;
    }
    Ok(format!(
        "{} absent/malformed fixtures fail closed",
        checked
    ))
}

/// Structural check that every measurable covers every required fixture
/// class (DP-5/DP-6/DP-8/DP-10 aggregate).
pub fn verify_fixture_pack_coverage(catalog: &DistinctionCatalog) -> Result<(), String> {
    for binding in &catalog.bindings {
        for class in FixtureClass::all() {
            let found = catalog.fixtures.iter().any(|f| {
                f.measurable_id == binding.contract_measurable_id && f.fixture_class == *class
            });
            if !found {
                return Err(format!(
                    "measurable {} missing required fixture class {}",
                    binding.contract_measurable_id,
                    class.as_str()
                ));
            }
        }
    }
    Ok(())
}

pub fn verify_fixture_expectations(catalog: &DistinctionCatalog) -> Result<(), String> {
    for fx in &catalog.fixtures {
        let row = evaluate_fixture(catalog, fx)?;
        if row.verdict != fx.expected_verdict {
            return Err(format!(
                "fixture {} expected {} but evaluator produced {} (reason: {:?})",
                fx.fixture_id,
                fx.expected_verdict.as_str(),
                row.verdict.as_str(),
                row.unresolved_reason
            ));
        }
    }
    Ok(())
}

pub fn distinction_report_markdown(fail_on_regression: bool) -> Result<String, String> {
    let catalog = demo_catalog();
    verify_fixture_pack_coverage(&catalog)?;
    verify_fixture_expectations(&catalog)?;
    render_report(
        &catalog,
        "STIG Expert Critic distinction-preserving walking skeleton",
        fail_on_regression,
    )
}

pub fn distinction_stig_report_markdown(fail_on_regression: bool) -> Result<String, String> {
    let catalog = crate::stig_catalog::stig_catalog()?;
    verify_fixture_pack_coverage(&catalog)?;
    verify_fixture_expectations(&catalog)?;
    render_report(
        &catalog,
        "F5 BIG-IP STIG full catalog (67 V-IDs) distinction-preserving gates",
        fail_on_regression,
    )
}

/// Serialize the full STIG distinction catalog, all evaluated fixture rows,
/// and DP gate results into a single JSON bundle that downstream projection
/// layers can consume without re-evaluating the criteria DSL.
pub fn distinction_stig_export_json() -> Result<String, String> {
    let catalog = crate::stig_catalog::stig_catalog()?;
    let capture_recipes = crate::stig_catalog::stig_capture_recipes()?;
    verify_fixture_pack_coverage(&catalog)?;
    verify_fixture_expectations(&catalog)?;
    let rows = run_factory_rows(&catalog)?;
    let gates = run_all_dp_gates(&catalog);
    let operator_set: BTreeSet<String> = catalog
        .partitions
        .iter()
        .map(|p| p.comparison_operator.clone())
        .collect();
    let bundle = serde_json::json!({
        "schema": "FactoryDistinctionBundle",
        "version": 1,
        "schemaVersion": "1.1.0",
        "bindings": catalog.bindings,
        "partitions": catalog.partitions,
        "equivalenceClasses": catalog.equivalence_classes,
        "fixtures": catalog.fixtures,
        "evaluatedRows": rows,
        "dpGates": gates,
        "captureRecipes": capture_recipes,
        "operatorSet": operator_set,
        "bundleProvenance": {
            "contractsPath": "docs/assertion_contracts.json",
            "exportCommand": "icf distinction stig-export",
            "trustRoot": "rust_factory"
        },
        "bindingCount": catalog.bindings.len(),
        "fixtureCount": catalog.fixtures.len(),
    });
    serde_json::to_string_pretty(&bundle)
        .map_err(|e| format!("JSON serialization failed: {e}"))
}

fn render_report(
    catalog: &DistinctionCatalog,
    subject: &str,
    fail_on_regression: bool,
) -> Result<String, String> {
    let reports = run_all_dp_gates(catalog);
    let mut output = String::new();
    output.push_str("# Distinction-Preserving Pullback Gate Report\n\n");
    output.push_str(&format!("Subject: {subject}\n\n"));
    output.push_str(&format!(
        "Bindings: {} | Fixtures: {} | Rows evaluated: {}\n\n",
        catalog.bindings.len(),
        catalog.fixtures.len(),
        catalog.fixtures.len(),
    ));
    output.push_str("| Gate | Dimension | Status | Details |\n");
    output.push_str("| --- | --- | --- | --- |\n");
    let mut failing = Vec::new();
    for r in &reports {
        output.push_str(&format!(
            "| {} | {} | {} | {} |\n",
            r.gate_id,
            r.dimension,
            r.status.as_str(),
            r.details
        ));
        if matches!(r.status, DpGateStatus::Fail) {
            failing.push(r.gate_id);
        }
    }
    if !failing.is_empty() {
        output.push_str(&format!("\nFailing gates: {}\n", failing.join(", ")));
        if fail_on_regression {
            return Err(output);
        }
    } else {
        output.push_str("\nAll DP-1..DP-10 gates pass.\n");
    }
    Ok(output)
}

// --------------------------------------------------------------------------
// Demo catalog (walking skeleton; preserved for reference + backwards-compat
// tests).
// --------------------------------------------------------------------------

pub fn demo_catalog() -> DistinctionCatalog {
    let banner_scope = "f5-bigip:ltm:standalone:fixture".to_string();
    let ssh_scope = "f5-bigip:sys:standalone:fixture".to_string();
    let fw_scope = "f5-bigip:ltm:standalone:fixture".to_string();

    let bindings = vec![
        MeasurableBinding {
            contract_measurable_id: "demo.banner.approved".to_string(),
            runtime_source_paths: vec!["banner_text".to_string()],
            projection_fn_id: "select_banner_text".to_string(),
            atomic_value_type: AtomicValueType::Token,
            lawful_partition_id: "partition.banner.approved".to_string(),
            representation_equivalence_class_ids: Vec::new(),
            scope_id: banner_scope.clone(),
            source_stig_clause: "STIG V-00001: banner must be APPROVED".to_string(),
            adapter_interpretation_note:
                "banner_text equality against canonical APPROVED literal; no casing folded"
                    .to_string(),
            lawful_partition_rationale:
                "banner text is a single canonical token; any other token is a fail".to_string(),
            required_atomic_description: "banner_text == \"APPROVED\"".to_string(),
            org_defined_value: None,
        },
        MeasurableBinding {
            contract_measurable_id: "demo.ssh.idle_timeout".to_string(),
            runtime_source_paths: vec!["idle_timeout".to_string()],
            projection_fn_id: "select_idle_timeout_seconds".to_string(),
            atomic_value_type: AtomicValueType::Integer,
            lawful_partition_id: "partition.ssh.idle_timeout".to_string(),
            representation_equivalence_class_ids: Vec::new(),
            scope_id: ssh_scope.clone(),
            source_stig_clause: "STIG V-00002: idle_timeout must be bounded and enabled"
                .to_string(),
            adapter_interpretation_note:
                "idle_timeout=0 is the vendor encoding of `disabled`; it is NOT a compliant \
                 value of <=300 and must fail closed"
                    .to_string(),
            lawful_partition_rationale:
                "0 collapses to `disabled` operationally; clamp below to disabled=fail, and \
                 require 1..=300 as pass band"
                    .to_string(),
            required_atomic_description: "1 <= idle_timeout <= 300 (0 = disabled = fail)"
                .to_string(),
            org_defined_value: None,
        },
        MeasurableBinding {
            contract_measurable_id: "demo.fw.listen_port".to_string(),
            runtime_source_paths: vec!["listen_port".to_string()],
            projection_fn_id: "select_listen_port_token".to_string(),
            atomic_value_type: AtomicValueType::Token,
            lawful_partition_id: "partition.fw.listen_port".to_string(),
            representation_equivalence_class_ids: vec!["equiv.fw.any_port".to_string()],
            scope_id: fw_scope.clone(),
            source_stig_clause: "STIG V-00003: management port must not be wildcarded".to_string(),
            adapter_interpretation_note:
                "`0`, `any`, `.0`, and the vendor alias `wildcard` all encode the same \
                 any-port wildcard; they must all canonicalize to the same fail token"
                    .to_string(),
            lawful_partition_rationale:
                "operationally all four encodings mean `any port`, which violates the STIG; \
                 they must fail identically"
                    .to_string(),
            required_atomic_description: "listen_port NOT in {any_port}".to_string(),
            org_defined_value: None,
        },
    ];

    let partitions = vec![
        LawfulPartition {
            partition_id: "partition.banner.approved".to_string(),
            measurable_id: "demo.banner.approved".to_string(),
            pass_predicates: vec![PartitionPredicate::EqualsToken("APPROVED".to_string())],
            fail_predicates: vec![
                PartitionPredicate::EqualsToken("DENIED".to_string()),
                PartitionPredicate::EqualsToken("WARN".to_string()),
                PartitionPredicate::EqualsToken("".to_string()),
            ],
            comparison_operator: "token_eq".to_string(),
            rationale: "banner must match the canonical APPROVED literal exactly".to_string(),
        },
        LawfulPartition {
            partition_id: "partition.ssh.idle_timeout".to_string(),
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            pass_predicates: vec![PartitionPredicate::IntClosedRange { lo: 1, hi: 300 }],
            fail_predicates: vec![
                PartitionPredicate::IntEqualsSentinel(0),
                PartitionPredicate::IntClosedRange {
                    lo: 301,
                    hi: i64::MAX,
                },
                PartitionPredicate::IntClosedRange {
                    lo: i64::MIN,
                    hi: -1,
                },
            ],
            comparison_operator: "int_partition".to_string(),
            rationale: "0 is operationally `disabled` and must not collapse into <=300".to_string(),
        },
        LawfulPartition {
            partition_id: "partition.fw.listen_port".to_string(),
            measurable_id: "demo.fw.listen_port".to_string(),
            pass_predicates: vec![PartitionPredicate::NotInSet(vec!["any_port".to_string()])],
            fail_predicates: vec![PartitionPredicate::EqualsToken("any_port".to_string())],
            comparison_operator: "token_not_in_set".to_string(),
            rationale: "any_port canonicalizes all wildcard encodings, which is non-compliant"
                .to_string(),
        },
    ];

    let equivalence_classes = vec![RepresentationEquivalenceClass {
        class_id: "equiv.fw.any_port".to_string(),
        measurable_id: "demo.fw.listen_port".to_string(),
        canonical_encoding: "any_port".to_string(),
        equivalent_encodings: vec![
            "0".to_string(),
            "any".to_string(),
            ".0".to_string(),
            "wildcard".to_string(),
        ],
        normalization_rule:
            "collapse {0, any, .0, wildcard} into canonical token `any_port`; unknown encodings \
             survive unchanged and fail closed through the partition"
                .to_string(),
    }];

    let fixtures = build_demo_fixtures(&banner_scope, &ssh_scope, &fw_scope);

    DistinctionCatalog {
        bindings,
        partitions,
        equivalence_classes,
        fixtures,
    }
}

fn build_demo_fixtures(
    banner_scope: &str,
    ssh_scope: &str,
    fw_scope: &str,
) -> Vec<FixtureExpectation> {
    let banner_clause = "STIG V-00001: banner must be APPROVED".to_string();
    let ssh_clause = "STIG V-00002: idle_timeout must be bounded and enabled".to_string();
    let fw_clause = "STIG V-00003: management port must not be wildcarded".to_string();

    vec![
        FixtureExpectation {
            fixture_id: "fx.banner.good_minimal".to_string(),
            fixture_class: FixtureClass::GoodMinimal,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "banner_text".to_string(),
                value: "APPROVED".to_string(),
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "minimal known-good banner".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.bad_canonical".to_string(),
            fixture_class: FixtureClass::BadCanonical,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "banner_text".to_string(),
                value: "DENIED".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "canonical failing banner".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.bad_representation_variant".to_string(),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "banner_text".to_string(),
                value: "WARN".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "alternate fail encoding of banner".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.boundary_value".to_string(),
            fixture_class: FixtureClass::BoundaryValue,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "banner_text".to_string(),
                value: "".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "empty banner fails closed".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.disabled_state".to_string(),
            fixture_class: FixtureClass::DisabledState,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "banner_text".to_string(),
                value: "UNSET".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "UNSET maps to neither pass nor fail predicate: unresolved".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.absent_state".to_string(),
            fixture_class: FixtureClass::AbsentState,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Missing,
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "banner evidence completely absent".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.malformed_state".to_string(),
            fixture_class: FixtureClass::MalformedState,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::Malformed {
                field: "banner_text".to_string(),
                raw: "<<binary_blob_0xDEAD>>".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "malformed payload fails closed into unresolved".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.noisy_evidence".to_string(),
            fixture_class: FixtureClass::NoisyEvidence,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::NoisyField {
                target: ("banner_text".to_string(), "APPROVED".to_string()),
                distractors: vec![
                    ("banner_title".to_string(), "DENIED".to_string()),
                    ("profile_dump".to_string(), "blob-payload".to_string()),
                    ("banner_text_backup".to_string(), "WARN".to_string()),
                ],
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "DP-1/DP-2: projection must ignore proxy fields".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.proxy_only".to_string(),
            fixture_class: FixtureClass::NoisyEvidence,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::ProxyField {
                proxy_field: "banner_title".to_string(),
                proxy_value: "APPROVED".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "DP-1: proxy field cannot stand in for the declared runtime source".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.banner.out_of_scope_variant".to_string(),
            fixture_class: FixtureClass::OutOfScopeVariant,
            measurable_id: "demo.banner.approved".to_string(),
            raw_evidence: RawEvidence::OutOfScope {
                field: "banner_text".to_string(),
                value: "APPROVED".to_string(),
                observed_scope_id: "f5-bigip:ltm:cluster:untested".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: banner_clause.clone(),
            scope_id: banner_scope.to_string(),
            notes: "DP-8: out-of-scope variants cannot claim pass".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.good_minimal".to_string(),
            fixture_class: FixtureClass::GoodMinimal,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "idle_timeout".to_string(),
                value: "150".to_string(),
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "minimal good idle_timeout inside 1..=300".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.bad_canonical".to_string(),
            fixture_class: FixtureClass::BadCanonical,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "idle_timeout".to_string(),
                value: "600".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "over-limit idle_timeout".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.bad_representation_variant".to_string(),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "idle_timeout".to_string(),
                value: "7200".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "alternate over-limit value".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.boundary_value".to_string(),
            fixture_class: FixtureClass::BoundaryValue,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "idle_timeout".to_string(),
                value: "300".to_string(),
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "boundary value at upper limit must still pass".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.disabled_state".to_string(),
            fixture_class: FixtureClass::DisabledState,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "idle_timeout".to_string(),
                value: "0".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "DP-3: 0 = disabled = fail, must not collapse into <=300".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.absent_state".to_string(),
            fixture_class: FixtureClass::AbsentState,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Missing,
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "idle_timeout evidence completely absent".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.noisy_evidence".to_string(),
            fixture_class: FixtureClass::NoisyEvidence,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::NoisyField {
                target: ("idle_timeout".to_string(), "120".to_string()),
                distractors: vec![
                    ("idle_timeout_backup".to_string(), "600".to_string()),
                    ("session_timeout".to_string(), "9999".to_string()),
                ],
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "noisy payload with compliant target field".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.malformed_state".to_string(),
            fixture_class: FixtureClass::MalformedState,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::Malformed {
                field: "idle_timeout".to_string(),
                raw: "three-hundred".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "malformed payload fails closed into unresolved".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.ssh.out_of_scope_variant".to_string(),
            fixture_class: FixtureClass::OutOfScopeVariant,
            measurable_id: "demo.ssh.idle_timeout".to_string(),
            raw_evidence: RawEvidence::OutOfScope {
                field: "idle_timeout".to_string(),
                value: "150".to_string(),
                observed_scope_id: "f5-bigip:sys:cluster:untested".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: ssh_clause.clone(),
            scope_id: ssh_scope.to_string(),
            notes: "DP-8: cluster topology never survived, cannot import pass".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.good_minimal".to_string(),
            fixture_class: FixtureClass::GoodMinimal,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "8443".to_string(),
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "concrete listen_port, not wildcard".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.bad_canonical".to_string(),
            fixture_class: FixtureClass::BadCanonical,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "any_port".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "canonical wildcard fails".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.bad_representation_variant_zero".to_string(),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "0".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "vendor encoding `0` for any_port, must fail identically".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.bad_representation_variant_any".to_string(),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "any".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "vendor encoding `any`, must fail identically".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.bad_representation_variant_dotzero".to_string(),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: ".0".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "vendor dotted encoding `.0`, must fail identically".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.disabled_state".to_string(),
            fixture_class: FixtureClass::DisabledState,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "wildcard".to_string(),
            },
            expected_verdict: Verdict::Fail,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "`wildcard` alias collapses to any_port".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.boundary_value".to_string(),
            fixture_class: FixtureClass::BoundaryValue,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Field {
                field: "listen_port".to_string(),
                value: "1".to_string(),
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "boundary: port 1 is concrete and passes".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.absent_state".to_string(),
            fixture_class: FixtureClass::AbsentState,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Missing,
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "listen_port evidence completely absent".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.malformed_state".to_string(),
            fixture_class: FixtureClass::MalformedState,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::Malformed {
                field: "listen_port".to_string(),
                raw: "<<adapter_cannot_parse>>".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "malformed payload fails closed into unresolved".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.noisy_evidence".to_string(),
            fixture_class: FixtureClass::NoisyEvidence,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::NoisyField {
                target: ("listen_port".to_string(), "8443".to_string()),
                distractors: vec![
                    ("listen_port_fallback".to_string(), "0".to_string()),
                    ("profile_blob".to_string(), "opaque".to_string()),
                ],
            },
            expected_verdict: Verdict::Pass,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "noisy but target field compliant".to_string(),
        },
        FixtureExpectation {
            fixture_id: "fx.fw.out_of_scope_variant".to_string(),
            fixture_class: FixtureClass::OutOfScopeVariant,
            measurable_id: "demo.fw.listen_port".to_string(),
            raw_evidence: RawEvidence::OutOfScope {
                field: "listen_port".to_string(),
                value: "8443".to_string(),
                observed_scope_id: "f5-bigip:ltm:cluster:untested".to_string(),
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: fw_clause.clone(),
            scope_id: fw_scope.to_string(),
            notes: "DP-8: untested cluster topology does not import pass".to_string(),
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn catalog_round_trip() {
        let catalog = demo_catalog();
        verify_fixture_pack_coverage(&catalog).expect("fixture pack covers required classes");
        verify_fixture_expectations(&catalog).expect("every fixture matches evaluator verdict");
    }

    #[test]
    fn all_ten_gates_pass_on_demo() {
        let catalog = demo_catalog();
        for r in run_all_dp_gates(&catalog) {
            assert!(
                matches!(r.status, DpGateStatus::Pass),
                "gate {} failed: {}",
                r.gate_id,
                r.details
            );
        }
    }

    #[test]
    fn live_request_matches_demo_good_fixture() {
        let catalog = demo_catalog();
        let request = LiveEvaluationRequest {
            measurable_id: "demo.banner.approved".to_string(),
            field_map: BTreeMap::from([("banner_text".to_string(), "APPROVED".to_string())]),
            raw_evidence: None,
            observed_scope_id: Some("f5-bigip:ltm:standalone:fixture".to_string()),
            evidence_source: "test::field_map".to_string(),
        };
        let response = evaluate_live_request(&catalog, &request).expect("live response");
        assert_eq!(response.status, "not_a_finding");
        assert_eq!(response.row.verdict, "pass");
        assert_eq!(response.row.partition_class, "compliant");
    }

    #[test]
    fn live_request_out_of_scope_is_unresolved() {
        let catalog = demo_catalog();
        let request = LiveEvaluationRequest {
            measurable_id: "demo.banner.approved".to_string(),
            field_map: BTreeMap::from([("banner_text".to_string(), "APPROVED".to_string())]),
            raw_evidence: None,
            observed_scope_id: Some("other:scope".to_string()),
            evidence_source: "test::field_map".to_string(),
        };
        let response = evaluate_live_request(&catalog, &request).expect("live response");
        assert_eq!(response.status, "insufficient_evidence");
        assert_eq!(response.row.verdict, "unresolved");
    }
}

//! Build a `DistinctionCatalog` that covers every F5 BIG-IP STIG V-ID in
//! `docs/assertion_contracts.json`.
//!
//! For each of the 67 contracts this produces:
//!   * one `MeasurableBinding` (with declared runtime sources, atomic type,
//!     scope, STIG clause anchor, partition rationale);
//!   * one `LawfulPartition` derived from `criteria.not_a_finding`
//!     (pass) and `criteria.open` (fail);
//!   * zero-or-more `RepresentationEquivalenceClass`es (bool normalization);
//!   * the full 9-class fixture pack (good_minimal, bad_canonical,
//!     bad_representation_variant, boundary_value, disabled_state,
//!     absent_state, malformed_state, noisy_evidence, out_of_scope_variant).
//!
//! The criteria DSL observed in the catalog:
//!   * homogeneous connectives per tree: either all AND or all OR;
//!   * operators == != <= >= < > ;
//!   * values: Int, Bool (`true`/`false`), quoted Token (`'informational'`),
//!     or the symbolic reference `org_defined_value`.
//! The parser refuses anything outside this grammar so any catalog drift
//! will surface as a `Result::Err`.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;

use serde_json::Value;

use crate::distinction::{
    AtomicValueType, CaptureSource, CaptureSourceKind, CmpOp, DistinctionCatalog, ExtractionRule,
    FixtureClass, FixtureExpectation, LawfulPartition, LiveCaptureRecipe, MeasurableBinding,
    PartitionPredicate, RawEvidence, RepresentationEquivalenceClass, Term, TermValue, Verdict,
};

const CONTRACTS_PATH: &str = "docs/assertion_contracts.json";
const SCOPE_NDM: &str = "f5-bigip:ndm:device:fixture";
const SCOPE_LTM: &str = "f5-bigip:ltm:device:fixture";
const SCOPE_APM: &str = "f5-bigip:apm:device:fixture";
const SCOPE_OUT_OF_SCOPE: &str = "f5-bigip:cluster:untested:fixture";
const ORG_DEFINED_INT: i64 = 25;

pub fn stig_catalog() -> Result<DistinctionCatalog, String> {
    load_stig_catalog(CONTRACTS_PATH)
}

pub fn stig_capture_recipes() -> Result<Vec<LiveCaptureRecipe>, String> {
    load_stig_capture_recipes(CONTRACTS_PATH)
}

pub fn load_stig_catalog(path: &str) -> Result<DistinctionCatalog, String> {
    let raw = fs::read_to_string(path).map_err(|e| format!("failed to read {path}: {e}"))?;
    let doc: Value =
        serde_json::from_str(&raw).map_err(|e| format!("failed to parse {path}: {e}"))?;
    let contracts = doc
        .get("contracts")
        .and_then(Value::as_array)
        .ok_or_else(|| "assertion contracts file missing `contracts`".to_string())?;

    let mut catalog = DistinctionCatalog::default();

    for contract in contracts {
        build_from_contract(contract, &mut catalog)?;
    }
    Ok(catalog)
}

pub fn load_stig_capture_recipes(path: &str) -> Result<Vec<LiveCaptureRecipe>, String> {
    let catalog = load_stig_catalog(path)?;
    let raw = fs::read_to_string(path).map_err(|e| format!("failed to read {path}: {e}"))?;
    let doc: Value =
        serde_json::from_str(&raw).map_err(|e| format!("failed to parse {path}: {e}"))?;
    let contracts = doc
        .get("contracts")
        .and_then(Value::as_array)
        .ok_or_else(|| "assertion contracts file missing `contracts`".to_string())?;
    let mut recipes = Vec::with_capacity(contracts.len());
    for contract in contracts {
        recipes.push(build_capture_recipe(contract, &catalog)?);
    }
    Ok(recipes)
}

fn build_capture_recipe(
    contract: &Value,
    catalog: &DistinctionCatalog,
) -> Result<LiveCaptureRecipe, String> {
    let measurable_id = contract
        .get("vuln_id")
        .and_then(Value::as_str)
        .ok_or_else(|| "contract missing vuln_id".to_string())?
        .to_string();
    let runtime_family = contract
        .get("runtime_family")
        .and_then(Value::as_str)
        .unwrap_or("unknown")
        .to_string();
    let binding = catalog
        .binding(&measurable_id)
        .ok_or_else(|| format!("no binding for {measurable_id}"))?;
    let mut sources: Vec<CaptureSource> = Vec::new();
    for command in contract
        .get("tmsh_commands")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        sources.push(CaptureSource {
            source_id: format!("tmsh:{command}"),
            kind: CaptureSourceKind::Tmsh,
            locator: command.to_string(),
        });
    }
    for endpoint in contract
        .get("rest_endpoints")
        .and_then(Value::as_array)
        .into_iter()
        .flatten()
        .filter_map(Value::as_str)
    {
        sources.push(CaptureSource {
            source_id: format!("rest:{endpoint}"),
            kind: CaptureSourceKind::Rest,
            locator: endpoint.to_string(),
        });
    }
    let source_ids: Vec<String> = sources.iter().map(|s| s.source_id.clone()).collect();
    let extraction_rules = binding
        .runtime_source_paths
        .iter()
        .map(|field| ExtractionRule {
            field: field.clone(),
            source_ids: source_ids.clone(),
            aliases: field_aliases(field),
            json_pointer_candidates: json_pointer_candidates(field),
            tmsh_property_candidates: tmsh_property_candidates(field),
        })
        .collect();
    Ok(LiveCaptureRecipe {
        measurable_id,
        runtime_family,
        projection_kind: if binding.runtime_source_paths.len() > 1
            || matches!(binding.atomic_value_type, AtomicValueType::Tuple)
        {
            "tuple".to_string()
        } else {
            "scalar".to_string()
        },
        sources,
        extraction_rules,
    })
}

fn field_aliases(field: &str) -> Vec<String> {
    let parts: Vec<&str> = field.split('_').collect();
    let mut values = BTreeSet::new();
    values.insert(field.to_string());
    values.insert(field.replace('_', "-"));
    if parts.len() > 1 {
        values.insert(parts[1..].join("_"));
        values.insert(parts[1..].join("-"));
    }
    if parts.len() > 2 {
        values.insert(parts[2..].join("_"));
        values.insert(parts[2..].join("-"));
    }
    if parts.len() > 3 {
        values.insert(parts[parts.len() - 2..].join("_"));
        values.insert(parts[parts.len() - 2..].join("-"));
    }
    values.retain(|v| !v.is_empty());
    values.into_iter().collect()
}

fn json_pointer_candidates(field: &str) -> Vec<String> {
    let mut values = BTreeSet::new();
    for alias in field_aliases(field) {
        let camel = snake_to_camel(&alias.replace('-', "_"));
        values.insert(format!("/{}", alias.replace('_', "/")));
        values.insert(format!("/{}", alias.replace('-', "/")));
        values.insert(format!("/{}", alias));
        values.insert(format!("/{}", alias.replace('-', "_")));
        values.insert(format!("/{}", alias.replace('_', "-")));
        values.insert(format!("/{}", camel));
    }
    values.into_iter().collect()
}

fn tmsh_property_candidates(field: &str) -> Vec<String> {
    let mut values = BTreeSet::new();
    for alias in field_aliases(field) {
        values.insert(alias.replace('_', "-"));
        values.insert(alias.replace('-', "_"));
        values.insert(alias);
    }
    values.into_iter().collect()
}

fn snake_to_camel(value: &str) -> String {
    let mut out = String::new();
    for (index, part) in value.split('_').filter(|p| !p.is_empty()).enumerate() {
        if index == 0 {
            out.push_str(part);
        } else {
            let mut chars = part.chars();
            if let Some(first) = chars.next() {
                out.push(first.to_ascii_uppercase());
                out.push_str(chars.as_str());
            }
        }
    }
    out
}

fn build_from_contract(contract: &Value, catalog: &mut DistinctionCatalog) -> Result<(), String> {
    let vuln_id = contract
        .get("vuln_id")
        .and_then(Value::as_str)
        .ok_or_else(|| "contract missing vuln_id".to_string())?
        .to_string();
    let title = contract
        .get("title")
        .and_then(Value::as_str)
        .unwrap_or("")
        .to_string();
    let runtime_family = contract
        .get("runtime_family")
        .and_then(Value::as_str)
        .unwrap_or("ndm")
        .to_string();
    let severity = contract
        .get("severity")
        .and_then(Value::as_str)
        .unwrap_or("unspecified")
        .to_string();

    let pass_raw = contract
        .pointer("/criteria/not_a_finding")
        .and_then(Value::as_str)
        .ok_or_else(|| format!("{vuln_id}: missing criteria.not_a_finding"))?
        .to_string();
    let fail_raw = contract
        .pointer("/criteria/open")
        .and_then(Value::as_str)
        .ok_or_else(|| format!("{vuln_id}: missing criteria.open"))?
        .to_string();

    let evidence_fields: Vec<String> = contract
        .get("evidence_required")
        .and_then(Value::as_array)
        .map(|arr| {
            arr.iter()
                .filter_map(|v| v.as_str().map(str::to_string))
                .collect()
        })
        .unwrap_or_default();
    if evidence_fields.is_empty() {
        return Err(format!("{vuln_id}: evidence_required is empty"));
    }

    let pass_tree = parse_criteria(&pass_raw)
        .map_err(|e| format!("{vuln_id}: pass predicate parse error: {e}"))?;
    let fail_tree = parse_criteria(&fail_raw)
        .map_err(|e| format!("{vuln_id}: fail predicate parse error: {e}"))?;

    let declared_fields: BTreeSet<&str> = pass_tree
        .terms
        .iter()
        .chain(fail_tree.terms.iter())
        .map(|t| t.field.as_str())
        .collect();
    for field in declared_fields {
        if !evidence_fields.iter().any(|e| e == field) {
            return Err(format!(
                "{vuln_id}: predicate references `{field}` not in evidence_required"
            ));
        }
    }

    let field_kinds = field_value_kinds(&pass_tree, &fail_tree)?;
    // Atomic type: Tuple for multi-field, otherwise the unique field's kind.
    let atomic_value_type = if evidence_fields.len() > 1 {
        AtomicValueType::Tuple
    } else {
        match field_kinds
            .get(&evidence_fields[0])
            .copied()
            .unwrap_or(ValueKind::Token)
        {
            ValueKind::Int => AtomicValueType::Integer,
            ValueKind::Bool => AtomicValueType::Bool,
            ValueKind::Token => AtomicValueType::Token,
        }
    };
    // Whole-binding hint used by org_defined_value selection.
    let dominant_kind = if field_kinds.values().any(|k| *k == ValueKind::Int) {
        ValueKind::Int
    } else if field_kinds.values().any(|k| *k == ValueKind::Bool) {
        ValueKind::Bool
    } else {
        ValueKind::Token
    };
    let bool_fields: Vec<String> = field_kinds
        .iter()
        .filter(|(_, k)| **k == ValueKind::Bool)
        .map(|(f, _)| f.clone())
        .collect();

    let source_url = stig_source_url(contract);
    let source_stig_clause = format!(
        "STIG {vuln_id} ({severity}): {title}{}",
        if source_url.is_empty() {
            String::new()
        } else {
            format!(" [{source_url}]")
        }
    );

    let scope_id = scope_for_family(&runtime_family).to_string();

    let org_defined_value = if pass_tree.mentions_org_defined() || fail_tree.mentions_org_defined()
    {
        match dominant_kind {
            ValueKind::Int => Some(TermValue::Int(ORG_DEFINED_INT)),
            ValueKind::Bool => Some(TermValue::Bool(true)),
            ValueKind::Token => Some(TermValue::Token("org_value".to_string())),
        }
    } else {
        None
    };

    let adapter_interpretation_note = format!(
        "evaluator reads evidence fields {evidence_fields:?} as declared by \
         `{vuln_id}`'s assertion contract. Pass predicate: `{pass_raw}`. \
         Fail predicate: `{fail_raw}`. Tokens are compared verbatim (quote \
         stripping), booleans via {{true,false}}, integers by declared \
         operator. No proxy fields, no casing folded outside declared \
         equivalence classes."
    );
    let lawful_partition_rationale = format!(
        "pass = not_a_finding literal `{pass_raw}`; fail = open literal \
         `{fail_raw}`. Any value that matches fail first dominates; any \
         value that matches pass but not fail passes; all other values \
         (including malformed / disabled / out-of-scope / absent) remain \
         unresolved."
    );
    let required_atomic_description = format!("not_a_finding :: {pass_raw}");

    let mut equivalence_class_ids = Vec::new();
    if !bool_fields.is_empty() {
        let class_id_pos = format!("equiv::{vuln_id}::bool::true");
        catalog
            .equivalence_classes
            .push(RepresentationEquivalenceClass {
                class_id: class_id_pos.clone(),
                measurable_id: vuln_id.clone(),
                canonical_encoding: "true".to_string(),
                equivalent_encodings: vec![
                    "True".to_string(),
                    "TRUE".to_string(),
                    "1".to_string(),
                    "yes".to_string(),
                ],
                normalization_rule: format!(
                    "vendor boolean variants for fields {bool_fields:?} fold onto canonical \
                     `true`; anything else survives unchanged and fails closed through \
                     the partition"
                ),
            });
        let class_id_neg = format!("equiv::{vuln_id}::bool::false");
        catalog
            .equivalence_classes
            .push(RepresentationEquivalenceClass {
                class_id: class_id_neg.clone(),
                measurable_id: vuln_id.clone(),
                canonical_encoding: "false".to_string(),
                equivalent_encodings: vec![
                    "False".to_string(),
                    "FALSE".to_string(),
                    "0".to_string(),
                    "no".to_string(),
                ],
                normalization_rule: format!(
                    "vendor boolean variants for fields {bool_fields:?} fold onto canonical \
                     `false`; anything else survives unchanged"
                ),
            });
        equivalence_class_ids.push(class_id_pos);
        equivalence_class_ids.push(class_id_neg);
    }

    let binding = MeasurableBinding {
        contract_measurable_id: vuln_id.clone(),
        runtime_source_paths: evidence_fields.clone(),
        projection_fn_id: format!("project::{vuln_id}"),
        atomic_value_type: atomic_value_type.clone(),
        lawful_partition_id: format!("partition::{vuln_id}"),
        representation_equivalence_class_ids: equivalence_class_ids,
        scope_id: scope_id.clone(),
        source_stig_clause: source_stig_clause.clone(),
        adapter_interpretation_note,
        lawful_partition_rationale,
        required_atomic_description,
        org_defined_value: org_defined_value.clone(),
    };

    let partition = LawfulPartition {
        partition_id: format!("partition::{vuln_id}"),
        measurable_id: vuln_id.clone(),
        pass_predicates: vec![predicate_from_tree(&pass_tree)],
        fail_predicates: vec![predicate_from_tree(&fail_tree)],
        comparison_operator: tree_comparison_operator(&pass_tree, &fail_tree, &evidence_fields),
        rationale: format!(
            "pass=not_a_finding, fail=open; {} term(s) in pass / {} term(s) in fail",
            pass_tree.terms.len(),
            fail_tree.terms.len()
        ),
    };

    let fixtures = synthesize_fixture_pack(
        &vuln_id,
        &evidence_fields,
        &pass_tree,
        &fail_tree,
        &field_kinds,
        &atomic_value_type,
        &scope_id,
        &source_stig_clause,
        org_defined_value.as_ref(),
    )?;

    catalog.bindings.push(binding);
    catalog.partitions.push(partition);
    catalog.fixtures.extend(fixtures);

    Ok(())
}

fn stig_source_url(contract: &Value) -> String {
    let Some(sources) = contract
        .pointer("/provenance/sources")
        .and_then(Value::as_array)
    else {
        return String::new();
    };
    for source in sources {
        if source.get("kind").and_then(Value::as_str) == Some("external_reference") {
            if let Some(url) = source.get("url").and_then(Value::as_str) {
                return url.to_string();
            }
        }
    }
    String::new()
}

fn scope_for_family(family: &str) -> &'static str {
    match family.to_ascii_lowercase().as_str() {
        "ltm" => SCOPE_LTM,
        "apm" => SCOPE_APM,
        _ => SCOPE_NDM,
    }
}

// --------------------------------------------------------------------------
// Criteria DSL parser
// --------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Connective {
    And,
    Or,
    None,
}

#[derive(Debug, Clone)]
struct ParsedTree {
    connective: Connective,
    terms: Vec<Term>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ValueKind {
    Int,
    Bool,
    Token,
}

impl ParsedTree {
    fn mentions_org_defined(&self) -> bool {
        self.terms
            .iter()
            .any(|t| matches!(t.value, TermValue::OrgDefined))
    }
}

fn parse_criteria(input: &str) -> Result<ParsedTree, String> {
    let trimmed = input.trim();
    if trimmed.is_empty() {
        return Err("empty predicate".to_string());
    }
    // Split into terms by AND / OR, preserving which connective.
    let mut connective = Connective::None;
    let mut terms_raw: Vec<&str> = Vec::new();
    let mut current_start = 0usize;
    let bytes = trimmed.as_bytes();
    let mut i = 0usize;
    while i < bytes.len() {
        if let Some(conn) = match_keyword(trimmed, i, "AND") {
            let term = trimmed[current_start..i].trim();
            if !term.is_empty() {
                terms_raw.push(term);
            }
            if connective == Connective::None {
                connective = Connective::And;
            } else if connective != Connective::And {
                return Err(format!("mixed connectives in `{input}`"));
            }
            i = conn;
            current_start = i;
            continue;
        }
        if let Some(conn) = match_keyword(trimmed, i, "OR") {
            let term = trimmed[current_start..i].trim();
            if !term.is_empty() {
                terms_raw.push(term);
            }
            if connective == Connective::None {
                connective = Connective::Or;
            } else if connective != Connective::Or {
                return Err(format!("mixed connectives in `{input}`"));
            }
            i = conn;
            current_start = i;
            continue;
        }
        i += 1;
    }
    let last = trimmed[current_start..].trim();
    if !last.is_empty() {
        terms_raw.push(last);
    }

    let mut terms = Vec::with_capacity(terms_raw.len());
    for raw in terms_raw {
        terms.push(parse_term(raw)?);
    }
    if terms.is_empty() {
        return Err(format!("no terms in `{input}`"));
    }
    Ok(ParsedTree { connective, terms })
}

fn match_keyword(s: &str, at: usize, kw: &str) -> Option<usize> {
    let rest = &s[at..];
    if !rest.to_ascii_uppercase().starts_with(kw) {
        return None;
    }
    let left_ok = at == 0 || !is_word_byte(s.as_bytes()[at - 1]);
    let end = at + kw.len();
    let right_ok = end >= s.len() || !is_word_byte(s.as_bytes()[end]);
    if left_ok && right_ok {
        Some(end)
    } else {
        None
    }
}

fn is_word_byte(b: u8) -> bool {
    b.is_ascii_alphanumeric() || b == b'_'
}

fn parse_term(raw: &str) -> Result<Term, String> {
    // field op value
    let trimmed = raw.trim();
    let mut op: Option<(CmpOp, usize, usize)> = None;
    // Order matters: two-char ops first.
    for (sym, cmp) in [
        ("==", CmpOp::Eq),
        ("!=", CmpOp::Ne),
        ("<=", CmpOp::Le),
        (">=", CmpOp::Ge),
    ] {
        if let Some(idx) = trimmed.find(sym) {
            op = Some((cmp, idx, idx + sym.len()));
            break;
        }
    }
    if op.is_none() {
        for (sym, cmp) in [("<", CmpOp::Lt), (">", CmpOp::Gt)] {
            if let Some(idx) = trimmed.find(sym) {
                // Avoid matching the trailing char of '<=' or '>=' which
                // we've already handled; since we checked above, any '<' or
                // '>' here is standalone.
                op = Some((cmp, idx, idx + sym.len()));
                break;
            }
        }
    }
    let (cmp, op_start, op_end) = op.ok_or_else(|| format!("no operator in term `{raw}`"))?;
    let field = trimmed[..op_start].trim();
    let value_raw = trimmed[op_end..].trim();
    if field.is_empty() {
        return Err(format!("missing field in term `{raw}`"));
    }
    if value_raw.is_empty() {
        return Err(format!("missing value in term `{raw}`"));
    }
    let value = parse_value(value_raw)?;
    Ok(Term {
        field: field.to_string(),
        op: cmp,
        value,
    })
}

fn parse_value(raw: &str) -> Result<TermValue, String> {
    let v = raw.trim();
    if v == "true" {
        return Ok(TermValue::Bool(true));
    }
    if v == "false" {
        return Ok(TermValue::Bool(false));
    }
    // Any organization-supplied symbolic reference (`org_defined_value`,
    // `org_defined_session_limit`, ...) folds onto the binding's
    // org_defined_value slot.
    if v.starts_with("org_defined_") {
        return Ok(TermValue::OrgDefined);
    }
    if (v.starts_with('\'') && v.ends_with('\'') && v.len() >= 2)
        || (v.starts_with('"') && v.ends_with('"') && v.len() >= 2)
    {
        return Ok(TermValue::Token(v[1..v.len() - 1].to_string()));
    }
    if let Ok(i) = v.parse::<i64>() {
        return Ok(TermValue::Int(i));
    }
    // Bare identifier (unquoted token)
    if v.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        return Ok(TermValue::Token(v.to_string()));
    }
    Err(format!("unrecognized value `{raw}`"))
}

fn field_value_kinds(
    pass: &ParsedTree,
    fail: &ParsedTree,
) -> Result<BTreeMap<String, ValueKind>, String> {
    let mut per_field: BTreeMap<String, BTreeSet<&'static str>> = BTreeMap::new();
    for term in pass.terms.iter().chain(fail.terms.iter()) {
        let entry = per_field.entry(term.field.clone()).or_default();
        match &term.value {
            TermValue::Int(_) => {
                entry.insert("int");
            }
            TermValue::Bool(_) => {
                entry.insert("bool");
            }
            TermValue::Token(_) => {
                entry.insert("token");
            }
            TermValue::OrgDefined => {}
        }
    }
    let mut out = BTreeMap::new();
    for (field, kinds) in per_field {
        if kinds.len() > 1 {
            return Err(format!("field `{field}` has mixed value kinds: {kinds:?}"));
        }
        let kind = match kinds.into_iter().next().unwrap_or("token") {
            "int" => ValueKind::Int,
            "bool" => ValueKind::Bool,
            _ => ValueKind::Token,
        };
        out.insert(field, kind);
    }
    Ok(out)
}

fn predicate_from_tree(tree: &ParsedTree) -> PartitionPredicate {
    match tree.connective {
        Connective::None | Connective::And => PartitionPredicate::AllOf(tree.terms.clone()),
        Connective::Or => PartitionPredicate::AnyOf(tree.terms.clone()),
    }
}

fn tree_comparison_operator(pass: &ParsedTree, fail: &ParsedTree, fields: &[String]) -> String {
    let pass_op = match pass.connective {
        Connective::And => "AND",
        Connective::Or => "OR",
        Connective::None => "SINGLE",
    };
    let fail_op = match fail.connective {
        Connective::And => "AND",
        Connective::Or => "OR",
        Connective::None => "SINGLE",
    };
    format!(
        "criteria_dsl[{}p/{}f;fields={}]",
        pass_op,
        fail_op,
        fields.len()
    )
}

// --------------------------------------------------------------------------
// Fixture synthesis
// --------------------------------------------------------------------------

#[allow(clippy::too_many_arguments)]
fn synthesize_fixture_pack(
    vuln_id: &str,
    fields: &[String],
    pass: &ParsedTree,
    fail: &ParsedTree,
    field_kinds: &BTreeMap<String, ValueKind>,
    atomic: &AtomicValueType,
    scope_id: &str,
    source_stig_clause: &str,
    org_defined: Option<&TermValue>,
) -> Result<Vec<FixtureExpectation>, String> {
    let pass_values = build_field_values(fields, pass, field_kinds, org_defined)?;
    let fail_values = build_field_values(fields, fail, field_kinds, org_defined)?;
    let fail_values_variant =
        build_field_values_variant(fields, fail, field_kinds, org_defined, &fail_values)?;
    let boundary_values =
        build_boundary_values(fields, pass, field_kinds, org_defined, &pass_values)?;

    let multi = fields.len() > 1 || matches!(atomic, AtomicValueType::Tuple);
    let mk_evidence = |values: &BTreeMap<String, String>| -> RawEvidence {
        if multi {
            RawEvidence::MultiField {
                fields: values.clone(),
            }
        } else {
            let (k, v) = values.iter().next().unwrap();
            RawEvidence::Field {
                field: k.clone(),
                value: v.clone(),
            }
        }
    };

    let distractor_fields: Vec<(String, String)> = vec![
        ("distract_alpha".to_string(), "junk_alpha".to_string()),
        ("distract_beta".to_string(), "junk_beta".to_string()),
        ("distract_gamma".to_string(), "999".to_string()),
    ];
    let mk_noisy = |values: &BTreeMap<String, String>| -> RawEvidence {
        if multi {
            RawEvidence::NoisyMultiField {
                target_fields: values.clone(),
                distractors: distractor_fields.clone(),
            }
        } else {
            let (k, v) = values.iter().next().unwrap();
            RawEvidence::NoisyField {
                target: (k.clone(), v.clone()),
                distractors: distractor_fields.clone(),
            }
        }
    };

    let mk_out_of_scope = |values: &BTreeMap<String, String>| -> RawEvidence {
        if multi {
            RawEvidence::OutOfScopeMultiField {
                fields: values.clone(),
                observed_scope_id: SCOPE_OUT_OF_SCOPE.to_string(),
            }
        } else {
            let (k, v) = values.iter().next().unwrap();
            RawEvidence::OutOfScope {
                field: k.clone(),
                value: v.clone(),
                observed_scope_id: SCOPE_OUT_OF_SCOPE.to_string(),
            }
        }
    };

    let mk_malformed = || -> RawEvidence {
        // Pick the first declared field and produce a malformed payload.
        let field = fields
            .first()
            .cloned()
            .unwrap_or_else(|| "unknown".to_string());
        RawEvidence::Malformed {
            field,
            raw: "<<adapter_cannot_parse_disabled_sensor>>".to_string(),
        }
    };

    let scope = scope_id.to_string();
    let clause = source_stig_clause.to_string();

    let fixtures = vec![
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::good_minimal"),
            fixture_class: FixtureClass::GoodMinimal,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_evidence(&pass_values),
            expected_verdict: Verdict::Pass,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "minimal compliant evidence satisfying every pass term".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::bad_canonical"),
            fixture_class: FixtureClass::BadCanonical,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_evidence(&fail_values),
            expected_verdict: Verdict::Fail,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "canonical violating evidence satisfying the open predicate".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::bad_representation_variant"),
            fixture_class: FixtureClass::BadRepresentationVariant,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_evidence(&fail_values_variant),
            expected_verdict: Verdict::Fail,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "alternate violating representation; must fail identically (DP-4)".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::boundary_value"),
            fixture_class: FixtureClass::BoundaryValue,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_evidence(&boundary_values),
            expected_verdict: Verdict::Pass,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "boundary value on the compliant side; flips if off-by-one".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::disabled_state"),
            fixture_class: FixtureClass::DisabledState,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_malformed(),
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes:
                "adapter-side disabled/null sentinel; partition refuses to classify, stays unresolved"
                    .to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::absent_state"),
            fixture_class: FixtureClass::AbsentState,
            measurable_id: vuln_id.to_string(),
            raw_evidence: RawEvidence::Missing,
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "evidence completely absent; fails closed into UNRESOLVED".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::malformed_state"),
            fixture_class: FixtureClass::MalformedState,
            measurable_id: vuln_id.to_string(),
            raw_evidence: {
                let field = fields
                    .first()
                    .cloned()
                    .unwrap_or_else(|| "unknown".to_string());
                RawEvidence::Malformed {
                    field,
                    raw: "<<adapter_malformed_response>>".to_string(),
                }
            },
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "malformed payload cannot be parsed; fails closed into UNRESOLVED".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::noisy_evidence"),
            fixture_class: FixtureClass::NoisyEvidence,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_noisy(&pass_values),
            expected_verdict: Verdict::Pass,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "compliant target with distractor fields; distractors must not leak".to_string(),
        },
        FixtureExpectation {
            fixture_id: format!("fx::{vuln_id}::out_of_scope_variant"),
            fixture_class: FixtureClass::OutOfScopeVariant,
            measurable_id: vuln_id.to_string(),
            raw_evidence: mk_out_of_scope(&pass_values),
            expected_verdict: Verdict::Unresolved,
            source_stig_clause: clause.clone(),
            scope_id: scope.clone(),
            notes: "DP-8: evidence from undeclared scope cannot claim pass".to_string(),
        },
    ];
    Ok(fixtures)
}

fn default_value_for(kind: ValueKind) -> String {
    match kind {
        ValueKind::Int => "0".to_string(),
        ValueKind::Bool => "false".to_string(),
        ValueKind::Token => "unspecified".to_string(),
    }
}

fn build_field_values(
    fields: &[String],
    tree: &ParsedTree,
    field_kinds: &BTreeMap<String, ValueKind>,
    org_defined: Option<&TermValue>,
) -> Result<BTreeMap<String, String>, String> {
    let mut map = BTreeMap::new();
    for field in fields {
        let kind = field_kinds.get(field).copied().unwrap_or(ValueKind::Token);
        map.insert(field.clone(), default_value_for(kind));
    }
    let indices: Vec<usize> = match tree.connective {
        Connective::And | Connective::None => (0..tree.terms.len()).collect(),
        Connective::Or => {
            if tree.terms.is_empty() {
                Vec::new()
            } else {
                vec![0]
            }
        }
    };
    for idx in indices {
        let term = &tree.terms[idx];
        let value = satisfying_value(term, org_defined, 0)?;
        map.insert(term.field.clone(), value);
    }
    Ok(map)
}

fn build_field_values_variant(
    fields: &[String],
    tree: &ParsedTree,
    field_kinds: &BTreeMap<String, ValueKind>,
    org_defined: Option<&TermValue>,
    canonical: &BTreeMap<String, String>,
) -> Result<BTreeMap<String, String>, String> {
    let _ = fields;
    let _ = field_kinds;
    let mut map = canonical.clone();
    let indices: Vec<usize> = match tree.connective {
        Connective::And | Connective::None => (0..tree.terms.len()).collect(),
        Connective::Or => {
            if tree.terms.is_empty() {
                Vec::new()
            } else {
                vec![0]
            }
        }
    };
    for idx in indices {
        let term = &tree.terms[idx];
        let mut variant_value = satisfying_value(term, org_defined, 1)?;
        if canonical.get(&term.field) == Some(&variant_value) {
            variant_value = satisfying_value(term, org_defined, 2)?;
        }
        map.insert(term.field.clone(), variant_value);
    }
    Ok(map)
}

fn build_boundary_values(
    fields: &[String],
    pass: &ParsedTree,
    field_kinds: &BTreeMap<String, ValueKind>,
    org_defined: Option<&TermValue>,
    pass_values: &BTreeMap<String, String>,
) -> Result<BTreeMap<String, String>, String> {
    let _ = fields;
    let _ = field_kinds;
    let mut map = pass_values.clone();
    let indices: Vec<usize> = match pass.connective {
        Connective::And | Connective::None => (0..pass.terms.len()).collect(),
        Connective::Or => {
            if pass.terms.is_empty() {
                Vec::new()
            } else {
                vec![0]
            }
        }
    };
    for idx in indices {
        let term = &pass.terms[idx];
        let boundary = boundary_value(term, org_defined)?;
        map.insert(term.field.clone(), boundary);
    }
    Ok(map)
}

/// Produce a value for `field` that satisfies `term`. `nonce` lets callers
/// request alternate encodings (canonical vs. variant) when the predicate
/// leaves a degree of freedom.
fn satisfying_value(
    term: &Term,
    org_defined: Option<&TermValue>,
    nonce: i64,
) -> Result<String, String> {
    let value = resolve_value(&term.value, org_defined)?;
    match (&value, term.op) {
        (TermValue::Int(target), CmpOp::Eq) => Ok(target.to_string()),
        (TermValue::Int(target), CmpOp::Ne) => Ok((target + 7 + nonce).to_string()),
        (TermValue::Int(target), CmpOp::Le) => Ok((target.saturating_sub(1 + nonce)).to_string()),
        (TermValue::Int(target), CmpOp::Ge) => Ok((target + 1 + nonce).to_string()),
        (TermValue::Int(target), CmpOp::Lt) => Ok((target.saturating_sub(1 + nonce)).to_string()),
        (TermValue::Int(target), CmpOp::Gt) => Ok((target + 1 + nonce).to_string()),
        (TermValue::Bool(target), CmpOp::Eq) => Ok(target.to_string()),
        (TermValue::Bool(target), CmpOp::Ne) => Ok((!*target).to_string()),
        (TermValue::Bool(_), _) => Err(format!(
            "boolean term `{}` uses unsupported operator `{}`",
            term.field,
            term.op.as_str()
        )),
        (TermValue::Token(target), CmpOp::Eq) => Ok(target.clone()),
        (TermValue::Token(target), CmpOp::Ne) => Ok(format!("{target}_variant_{nonce}")),
        (TermValue::Token(_), _) => Err(format!(
            "token term `{}` uses unsupported operator `{}`",
            term.field,
            term.op.as_str()
        )),
        (TermValue::OrgDefined, _) => Err(format!(
            "org_defined_value term `{}` unresolved (no binding org value)",
            term.field
        )),
    }
}

/// Boundary value on the compliant side of `term`.
fn boundary_value(term: &Term, org_defined: Option<&TermValue>) -> Result<String, String> {
    let value = resolve_value(&term.value, org_defined)?;
    match (&value, term.op) {
        (TermValue::Int(target), CmpOp::Le) => Ok(target.to_string()),
        (TermValue::Int(target), CmpOp::Ge) => Ok(target.to_string()),
        (TermValue::Int(target), CmpOp::Lt) => Ok((target - 1).to_string()),
        (TermValue::Int(target), CmpOp::Gt) => Ok((target + 1).to_string()),
        (TermValue::Int(target), CmpOp::Eq) => Ok(target.to_string()),
        (TermValue::Int(target), CmpOp::Ne) => Ok((target + 1).to_string()),
        (TermValue::Bool(target), CmpOp::Eq) => Ok(target.to_string()),
        (TermValue::Bool(target), CmpOp::Ne) => Ok((!*target).to_string()),
        (TermValue::Bool(_), _) => Err("bool ordering has no boundary".to_string()),
        (TermValue::Token(target), CmpOp::Eq) => Ok(target.clone()),
        (TermValue::Token(target), CmpOp::Ne) => Ok(format!("{target}_boundary")),
        (TermValue::Token(_), _) => Err("token ordering has no boundary".to_string()),
        (TermValue::OrgDefined, _) => Err("org_defined_value unresolved".to_string()),
    }
}

fn resolve_value(value: &TermValue, org_defined: Option<&TermValue>) -> Result<TermValue, String> {
    match value {
        TermValue::OrgDefined => org_defined
            .cloned()
            .ok_or_else(|| "org_defined_value unresolved".to_string()),
        other => Ok(other.clone()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::distinction::{
        run_all_dp_gates, verify_fixture_expectations, verify_fixture_pack_coverage, DpGateStatus,
    };

    #[test]
    fn catalog_loads_and_covers_all_vids() {
        let catalog = stig_catalog().expect("catalog");
        assert!(
            catalog.bindings.len() >= 60,
            "too few bindings: {}",
            catalog.bindings.len()
        );
        verify_fixture_pack_coverage(&catalog).expect("fixture pack coverage");
    }

    #[test]
    fn catalog_expectations_match_evaluator() {
        let catalog = stig_catalog().expect("catalog");
        verify_fixture_expectations(&catalog).expect("evaluator matches expectations");
    }

    #[test]
    fn all_ten_gates_pass_on_stig_catalog() {
        let catalog = stig_catalog().expect("catalog");
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
    fn capture_recipe_exists_for_every_binding() {
        let catalog = stig_catalog().expect("catalog");
        let recipes = stig_capture_recipes().expect("recipes");
        assert_eq!(recipes.len(), catalog.bindings.len());
        for binding in &catalog.bindings {
            assert!(
                recipes
                    .iter()
                    .any(|recipe| recipe.measurable_id == binding.contract_measurable_id),
                "missing capture recipe for {}",
                binding.contract_measurable_id
            );
        }
    }

    #[test]
    fn capture_recipe_fields_match_evidence_required() {
        let catalog = stig_catalog().expect("catalog");
        let recipes = stig_capture_recipes().expect("recipes");
        for recipe in &recipes {
            let binding = catalog
                .binding(&recipe.measurable_id)
                .expect("binding exists for recipe");
            let fields: Vec<&String> = recipe
                .extraction_rules
                .iter()
                .map(|rule| &rule.field)
                .collect();
            assert_eq!(fields.len(), binding.runtime_source_paths.len());
            for field in &binding.runtime_source_paths {
                assert!(
                    fields.iter().any(|candidate| *candidate == field),
                    "recipe {} missing field {}",
                    recipe.measurable_id,
                    field
                );
            }
        }
    }

    #[test]
    fn capture_recipe_sources_match_contract_commands() {
        let recipes = stig_capture_recipes().expect("recipes");
        for recipe in &recipes {
            assert!(
                !recipe.sources.is_empty(),
                "recipe {} missing capture sources",
                recipe.measurable_id
            );
            for source in &recipe.sources {
                assert!(
                    source.source_id.starts_with("tmsh:") || source.source_id.starts_with("rest:"),
                    "recipe {} has malformed source id {}",
                    recipe.measurable_id,
                    source.source_id
                );
                assert!(
                    !source.locator.trim().is_empty(),
                    "recipe {} has empty source locator",
                    recipe.measurable_id
                );
            }
        }
    }

    #[test]
    fn factory_export_contains_live_eval_inputs() {
        let bundle =
            crate::distinction::distinction_stig_export_json().expect("export bundle serializes");
        let doc: Value = serde_json::from_str(&bundle).expect("export bundle json");
        let recipes = doc
            .get("captureRecipes")
            .and_then(Value::as_array)
            .expect("captureRecipes array");
        assert!(
            !recipes.is_empty(),
            "export bundle must include capture recipes"
        );
        assert!(
            doc.get("operatorSet")
                .and_then(Value::as_array)
                .is_some_and(|items| !items.is_empty()),
            "export bundle must include operatorSet"
        );
        assert!(
            doc.get("bundleProvenance").is_some(),
            "export bundle must include bundleProvenance"
        );
    }
}

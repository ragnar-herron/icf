"""
bridge/family_evaluator.py

Parses the criteria DSL from assertion_contracts.json and evaluates
extracted evidence against it.  Returns AtomicPullbackRow per control.

Criteria DSL grammar (all 67 controls):
  expr     := clause (('AND'|'OR') clause)*
  clause   := field operator value
  operator := '==' | '!=' | '<=' | '>=' | '<' | '>'
  value    := integer | quoted_string | 'true' | 'false' | 'none'
            | field_ref | 'org_defined_value' | 'org_defined_session_limit'

The evaluator classifies each contract into a family automatically,
then dispatches to one of 4 evaluation functions.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class AtomicPullbackRow:
    vuln_id: str
    fields: dict[str, Any]
    required: dict[str, Any]
    observed: dict[str, Any]
    operator_summary: str
    verdict: str  # "pass" | "fail" | "unresolved"

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Load domain data
# ---------------------------------------------------------------------------

def load_contracts(root: Path = REPO_ROOT) -> list[dict]:
    p = root / "docs" / "assertion_contracts.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return data["contracts"]


def load_distinction_bundle(root: Path = REPO_ROOT) -> dict[str, dict]:
    p = root / "factory_exports" / "stig_expert_critic" / "data" / "FactoryDistinctionBundle.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return {b["contract_measurable_id"]: b for b in data["bindings"]}


# ---------------------------------------------------------------------------
# Criteria DSL tokenizer + parser
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(
    r"'[^']*'"          # quoted string
    r"|\"[^\"]*\""      # double-quoted string
    r"|AND|OR"          # logical connectors
    r"|[<>!=]+"         # operators
    r"|[\w.]+"          # identifiers and numbers
)


@dataclass
class Comparison:
    field: str
    op: str
    value: str  # raw token


@dataclass
class CriteriaExpr:
    clauses: list[Comparison]
    connectors: list[str]  # 'AND' or 'OR', len = len(clauses)-1


def parse_criteria(text: str) -> CriteriaExpr:
    tokens = _TOKEN_RE.findall(text)
    clauses: list[Comparison] = []
    connectors: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] in ("AND", "OR"):
            connectors.append(tokens[i])
            i += 1
            continue
        if i + 2 < len(tokens) and tokens[i + 1] in ("==", "!=", "<=", ">=", "<", ">"):
            clauses.append(Comparison(tokens[i], tokens[i + 1], tokens[i + 2]))
            i += 3
        else:
            i += 1
    return CriteriaExpr(clauses, connectors)


# ---------------------------------------------------------------------------
# Value coercion / resolution
# ---------------------------------------------------------------------------

def _resolve_value(raw: str, evidence: dict[str, Any], org_defined: dict | None) -> Any:
    is_quoted = (raw.startswith("'") and raw.endswith("'")) or \
                (raw.startswith('"') and raw.endswith('"'))
    stripped = raw.strip("'\"")

    if is_quoted:
        return stripped

    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw in ("org_defined_value", "org_defined_session_limit"):
        if org_defined and isinstance(org_defined, dict):
            return org_defined.get("Int", org_defined.get("String", org_defined.get("Bool")))
        return None
    if raw in evidence:
        return evidence[raw]

    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        pass

    if stripped.lower() == "enabled":
        return True
    if stripped.lower() == "disabled":
        return False
    if stripped.lower() == "none":
        return None
    return stripped


def _compare(observed: Any, op: str, required: Any) -> bool | None:
    """Return True/False for the comparison, or None if unresolvable."""
    if observed is None or required is None:
        return None

    if isinstance(observed, bool) and isinstance(required, str):
        required = required.lower() in ("true", "enabled", "on")
    if isinstance(required, bool) and isinstance(observed, str):
        observed = observed.lower() in ("true", "enabled", "on")

    if isinstance(required, (int, float)) and isinstance(observed, str):
        try:
            observed = int(observed)
        except ValueError:
            try:
                observed = float(observed)
            except ValueError:
                return None
    if isinstance(observed, (int, float)) and isinstance(required, str):
        try:
            required = int(required)
        except ValueError:
            try:
                required = float(required)
            except ValueError:
                pass

    if isinstance(observed, bool):
        observed = 1 if observed else 0
    if isinstance(required, bool):
        required = 1 if required else 0

    try:
        if op == "==":
            return observed == required
        if op == "!=":
            return observed != required
        if op == "<=":
            return observed <= required
        if op == ">=":
            return observed >= required
        if op == "<":
            return observed < required
        if op == ">":
            return observed > required
    except TypeError:
        if op == "==" and str(observed).lower() == str(required).lower():
            return True
        if op == "!=" and str(observed).lower() != str(required).lower():
            return True
        return None
    return None


# ---------------------------------------------------------------------------
# Evaluate a criteria expression against evidence
# ---------------------------------------------------------------------------

def evaluate_criteria(
    expr: CriteriaExpr,
    evidence: dict[str, Any],
    org_defined: dict | None = None,
) -> tuple[bool | None, dict[str, Any], dict[str, Any]]:
    """Evaluate a parsed criteria expression.

    Returns (result, required_map, observed_map).
    result is True (pass), False (fail), or None (unresolved).
    """
    required_map: dict[str, Any] = {}
    observed_map: dict[str, Any] = {}
    results: list[bool | None] = []

    for clause in expr.clauses:
        obs = evidence.get(clause.field)
        req = _resolve_value(clause.value, evidence, org_defined)
        observed_map[clause.field] = obs
        required_map[clause.field] = f"{clause.op} {clause.value}"

        cmp_result = _compare(obs, clause.op, req)
        results.append(cmp_result)

    if not results:
        return None, required_map, observed_map

    if not expr.connectors:
        return results[0], required_map, observed_map

    if all(c == "AND" for c in expr.connectors):
        if None in results:
            return None, required_map, observed_map
        return all(results), required_map, observed_map

    if all(c == "OR" for c in expr.connectors):
        if any(r is True for r in results):
            return True, required_map, observed_map
        if all(r is False for r in results):
            return False, required_map, observed_map
        return None, required_map, observed_map

    combined = results[0]
    for i, connector in enumerate(expr.connectors):
        next_r = results[i + 1]
        if connector == "AND":
            if combined is None or next_r is None:
                combined = None
            else:
                combined = combined and next_r
        else:
            if combined is True or next_r is True:
                combined = True
            elif combined is None or next_r is None:
                combined = None
            else:
                combined = combined or next_r
    return combined, required_map, observed_map


# ---------------------------------------------------------------------------
# Top-level: evaluate one control
# ---------------------------------------------------------------------------

def evaluate_control(
    contract: dict,
    evidence: dict[str, Any],
    binding: dict | None = None,
) -> AtomicPullbackRow:
    """Evaluate a single control's criteria against provided evidence.

    Returns an AtomicPullbackRow with verdict = pass/fail/unresolved.
    """
    vuln_id = contract["vuln_id"]
    naf_text = contract["criteria"]["not_a_finding"]
    open_text = contract["criteria"]["open"]

    org_defined = binding.get("org_defined_value") if binding else None

    naf_expr = parse_criteria(naf_text)
    open_expr = parse_criteria(open_text)

    open_result, _, _ = evaluate_criteria(open_expr, evidence, org_defined)
    if open_result is True:
        naf_result, required_map, observed_map = evaluate_criteria(naf_expr, evidence, org_defined)
        return AtomicPullbackRow(
            vuln_id=vuln_id,
            fields=list(contract["evidence_required"]),
            required=required_map,
            observed=observed_map,
            operator_summary=naf_text,
            verdict="fail",
        )

    naf_result, required_map, observed_map = evaluate_criteria(naf_expr, evidence, org_defined)
    if naf_result is True:
        verdict = "pass"
    elif naf_result is False:
        verdict = "fail"
    else:
        verdict = "unresolved"

    return AtomicPullbackRow(
        vuln_id=vuln_id,
        fields=list(contract["evidence_required"]),
        required=required_map,
        observed=observed_map,
        operator_summary=naf_text,
        verdict=verdict,
    )


def evaluate_all_contracts(
    contracts: list[dict],
    evidence_fn,
    bundle: dict[str, dict],
) -> list[AtomicPullbackRow]:
    """Evaluate all contracts. evidence_fn(vuln_id) -> dict of evidence."""
    rows = []
    for contract in contracts:
        vid = contract["vuln_id"]
        evidence = evidence_fn(vid)
        binding = bundle.get(vid)
        rows.append(evaluate_control(contract, evidence, binding))
    return rows


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from bridge.evidence_extractor import (
        extract_evidence_for_control,
        load_manifest,
        load_outcome_matrix,
    )

    manifest = load_manifest()
    matrix = load_outcome_matrix()
    contracts = load_contracts()
    bundle = load_distinction_bundle()

    pass_count = fail_count = unresolved_count = 0
    for contract in contracts:
        vid = contract["vuln_id"]
        evidence = extract_evidence_for_control(vid, matrix, manifest)
        binding = bundle.get(vid)
        row = evaluate_control(contract, evidence, binding)
        symbol = {"pass": "+", "fail": "X", "unresolved": "?"}[row.verdict]
        print(f"  [{symbol}] {vid}: {row.verdict}")
        if row.verdict == "pass":
            pass_count += 1
        elif row.verdict == "fail":
            fail_count += 1
        else:
            unresolved_count += 1

    total = len(contracts)
    print(f"\n  Summary: {pass_count} pass, {fail_count} fail, {unresolved_count} unresolved / {total} total")

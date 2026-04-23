# ICF Domain Coalgebra — Complete Specification

Version: `1.0.0`
Status: `normative`
Supersedes: `docs/coalgebra_test.md`, `docs/stig_coalgebra_test.md`, `docs/general_coalgebra_test.md`, `docs/distinction_preserving_test.md`, `docs/export_projection_profile_test.md`, `docs/stig_expert_critic_web_app_coalgebra.md`, `docs/correction_plan_v1.md`

This document is the **sole authoritative specification** for any domain coalgebra (first instance: STIG expert critic) built by the ICF factory. It consolidates all constraints, rules, laws, and principles into one artifact. If this document and a prior doc conflict, this document governs.

---

# Part I — Coalgebra Constitution

## 1. The Seven-Part Coalgebra Production Test

A system **produces a coalgebra** if and only if it answers all seven questions with explicit, machine-testable artifacts. No promotion, no export, no shipping is possible until all seven are answered.

### C1 — State

The system defines a closed state schema `X` with no free variables.

For the STIG domain:

```
X = {
  witness_registry      : Map<WitnessId, WitnessRecord>
  validator_registry    : Map<ValidatorId, ValidatorRecord>
  survivor_state        : Map<SubjectId, SurvivorChain>
  open_criticisms       : Set<CriticismRecord>
  open_falsifiers       : Set<FalsifierRecord>
  scope                 : ScopeRecord
  trust_state           : KeySetRecord
  adapter_registry      : Map<AdapterFamilyId, AdapterStatus>
  ledger_tip            : Hash
}
```

State is **not** a log, a rulebook, or an output.

### C2 — Observations

The system defines a closed observation space `O`:

```
O = {
  PullbackRecord
  FalsifierRecord
  CriticismRecord
  PromotionCandidateRecord
  PromotionRecord
  DemotionRecord
  ContradictionRecord
  SurvivorUpdateRecord
  AdapterLegitimacyRecord
  ExportProjectionGateRecord
}
```

### C3 — Events

The system defines a closed event space `I`:

```
I = {
  NewEvidence(EvidenceRecord)
  RunPullback(ClaimHandle, EvidenceSet, WitnessHandle, ValidatorHandle)
  BreakInjection(BreakRecord)
  FixApplication(FixRecord)
  SynthesisProposal(SynthesisProposalRecord)
  ScopeChange(ScopeRecord)
  TrustRootChange(KeySetRecord)
  AdapterCapture(AdapterCaptureRecord)
  AdapterReplay(AdapterReplayRecord)
  WitnessRetirement(WitnessRetirementRecord)
}
```

### C4 — Behavior Map

```
step : X × I → O* × X
```

`step` is the deterministic composition of `pullback_core::pullback`, `survivor_model` updates, and dependency-state binding (BUILD_SPEC §11). Given the same `(state, event)`, it produces byte-identical observations and successor state. Replay is the canonical definition of `step`.

### C5 — Behavioral Distinction

Two states `x₁, x₂` are **behaviorally distinct** if there exists an event `e ∈ I` such that `step(x₁, e)` and `step(x₂, e)` produce different observation sequences. Tested by trace comparison or bisimulation-style test suite.

### C6 — Falsifier

The coalgebra is falsified if:

- Same declared state + same event produces different observations (determinism violation)
- A recorded transition cannot be reproduced by `step` (replay failure)
- An observation outside `O` is emitted (observation leak)
- A promoted state behaves indistinguishably from an under-criticism state (distinction failure)

These are captured as `CoalgebraAdequacyRecord` and trigger immediate demotion.

### C7 — Scope

Every coalgebra declares scope as a set of environment axes with explicit values:

```
scope = {
  domain            : "stig" | "robotics" | <domain-tag>
  product           : "F5 BIG-IP"
  platform          : ["i-series", "viprion", "velos", ...]
  software_version  : ["17.5.x", ...]
  module            : ["ltm", "apm", "asm", "afm", ...]
  topology          : ["standalone", "ha-pair", "cluster"]
  credential_scope  : ["admin", "auditor", ...]
}
```

Out-of-scope inputs must return `OUT_OF_SCOPE` or `UNRESOLVED`, never a resolved verdict.

---

# Part II — Pullback Integrity (10 Laws)

These are **absolute laws**. No code path, no optimization, no shortcut may violate them. Every judgment flows through pullback.

### P1 — Declaration–Reality

No claim accepted without evidence-mediated witness comparison. Evidence and claim are distinct from judgment; the witness is the only legal comparison surface.

### P2 — Claim–Evidence Separation

Evidence is raw observation. Claim is structured assertion. Judgment is pullback output. The three are never conflated. Evidence is stored content-addressed in the blob store; metadata in the ledger.

### P3 — Witness–Reality

Witnesses are criticizable, revisable, versionable, and retirable. No witness is trusted; every witness earns status through survival under adversarial testing.

### P4 — Plan–Execution

Remediation advice is validated only via post-fix evidence. Advice ≠ truth. A fix is not complete until a new pullback against post-fix evidence passes with the same witness.

### P5 — Synthesis–Behavior

Synthesized artifacts (validators, adapters, scripts, proposals) remain hypotheses until they survive behavioral criticism. `SynthesisProposalRecord.status ∈ {proposal, retracted}` only.

### P6 — Failure–Survivor

Promoted survivors derive from preserved failures. Every promotion traces back through failure → criticism → survival lineage. No promotion without failure ancestry.

### P7 — Level–Level Consistency

Contradictions are detectable across abstraction layers (goal↔plan, plan↔design, design↔implementation, implementation↔behavior, behavior↔world). Detected contradictions produce `ContradictionRecord` and `CriticismRecord`.

### P8 — Revision–Identity

Changes are checked against stable task identity. Non-constitutive changes preserve identity; constitutive changes (altering core pullbacks, witness laws, promotion law) must be explicitly declared.

### P9 — Criticism–Memory

Criticism is durable, append-only, and replayable. Removing or overwriting a criticism record breaks the hash chain and is a hard verification failure.

### P10 — Optimization–Truth

No optimization may reduce falsifier yield, evidence visibility, or failure preservation. The waste heat ratio may only decrease while distinction integrity holds at zero.

---

# Part III — Distinction-Preserving Gates (10 Gates)

Every adapter, evaluator, and validator must pass **all 10 gates** before promotion. These gates are what prevent "4/9 legitimacy."

### DP-1 — Measurable Identity

The adapter measures the **exact** contract field and only that field. One contract measurable maps to one declared runtime source. No proxy fields, no silent aggregation.

**Falsifiers:** Known-good fixture where target field exists but proxy field differs. Known-bad fixture where proxy matches but true field fails.

### DP-2 — Atomic Pullback

The final comparison surface is irreducible: `{required_atomic, observed_atomic, operator, verdict}`. No lists, blobs, or composite structures on the comparison row unless the contract explicitly defines set-valued measurables.

**Falsifiers:** Noisy evidence fixture with correct atomic value plus distracting extra fields. Evaluator must reject or normalize explicitly.

### DP-3 — Lawful Distinction

The predicate preserves the real operational distinction the STIG cares about. For every measurable, define a **lawful partition**: `{compliant, noncompliant, disabled, absent, malformed, indeterminate}`. No collapse between operationally different states.

**Falsifiers:** One fixture for each boundary class. `0 = disabled = fail` must be distinct from `0 = compliant`.

### DP-4 — Representation Equivalence

All equivalent runtime encodings of the same state normalize identically. Port `0`, `any`, `.0`, vendor-specific wildcards → same atomic pullback value. Unknown encodings fail closed or go unresolved.

**Falsifiers:** Paired fixtures using equivalent encodings of the same bad state; both must fail identically.

### DP-5 — Known-Bad Must Fail

Every control ships with at least one **must-fail fixture**. The canonical bad state must fail at the final pullback row, citing the exact lawful measurable.

### DP-6 — Known-Good Must Survive

Every control ships with at least one **may-pass fixture**. The known-good state passes or provisionally passes with an attached falsifier.

### DP-7 — Factory/Export Equivalence

Factory and export are compared over the same fixture pack. Same pullback rows, same verdicts, same unresolved classes, same falsifier attachments, same scope warnings.

**Falsifiers:** Fixture pack diff between factory and export. Any row mismatch fails shipping.

### DP-8 — Scope Honesty

Promotion scope is bounded by tested fixtures. Untested representations remain out-of-scope or unresolved. No scope inflation.

**Falsifiers:** Out-of-scope fixture that the evaluator incorrectly treats as in-scope pass.

### DP-9 — Source Anchoring

Every operational distinction traces back to source requirement text (STIG clause) and forward to runtime evidence. No invented semantics.

**Falsifiers:** Control where source requirement is ambiguous and evaluator still claims certainty.

### DP-10 — Unresolved Honesty

When atomic truth cannot be preserved, the evaluator fails closed into `INSUFFICIENT_EVIDENCE` or `WITNESS_UNDER_CRITICISM`. Ambiguity is never collapsed into confidence.

**Falsifiers:** Truncated evidence, mixed representation, malformed payload.

---

# Part IV — Adapter Legitimacy (9/9 Required)

This is the concrete checklist that must reach **9/9**, not 4/9. An adapter family (e.g., `ltm_virtual_ssl`) is not legitimate until all 9 hold:

| # | Requirement | Evidence |
| - | ----------- | -------- |
| 1 | **Has contract DSL** | Control's criteria exist in the catalog with typed measurables |
| 2 | **Has capture evidence** | Real tmsh/REST samples checked into blob store from real device |
| 3 | **Has normalization mapping** | Explicit field extraction mapping from raw capture to atomic measurable |
| 4 | **Has fixture coverage** | All 9 fixture classes present (see §Part V) |
| 5 | **Passes replay** | Deterministic against captured data; `replay_fidelity == 1.0` |
| 6 | **Passes falsifiers** | Known-bad must fail; known-good must survive |
| 7 | **Passes equivalence** | Factory output == export output on the same fixture pack |
| 8 | **Has promotion record** | Signed promotion record with full survivor lineage |
| 9 | **Passes DP-1 through DP-10** | All 10 distinction-preserving gates satisfied |

**If any item is missing:**

```
adapter_status = NOT_LEGITIMATE
control_status = projected_unresolved
export_status  = PROJECTED_UNRESOLVED
```

No exceptions. No "capture_only" displayed as anything stronger.

---

# Part V — Mandatory Fixture Pack (Per Control)

Every control must carry **all 9 fixture classes**, each explicitly marked as `required`, `not_applicable`, or `deferred_with_reason`:

```
1. good_minimal            — minimal compliant state
2. bad_canonical           — canonical noncompliant state
3. bad_representation_variant — alternate encoding of the same bad state
4. boundary_value          — edge of compliant/noncompliant threshold
5. disabled_state          — feature/service disabled (operationally distinct from absent)
6. absent_state            — field/object missing entirely
7. malformed_state         — corrupted, truncated, or unparseable evidence
8. noisy_evidence          — correct value buried in extraneous data
9. out_of_scope_variant    — platform/version/topology outside declared scope
```

Missing fixture class without declared justification → **hard fail** of the adapter legitimacy gate.

---

# Part VI — Adapter Promotion Pipeline

This is the concrete lifecycle that closes the gap between "capture_only" and "promoted":

```
Step A — Capture
  Collect real tmsh/REST outputs from real device variants.
  Store as content-addressed blobs.

Step B — Normalize
  Write deterministic extractors to produce exact atomic measurable.
  Declare normalization mapping.

Step C — Fixture
  Build all 9 fixture classes.
  Each fixture declares expected pullback outcome.

Step D — Replay
  Run extracted values against all fixtures.
  replay_fidelity must equal 1.0.
  Known-bad must fail. Known-good must survive.

Step E — Distinction Gates
  Run DP-1 through DP-10.
  All must pass.

Step F — Export Equivalence
  Compare factory output to export output.
  projection_equivalence_rate must equal 1.0.

Step G — Promote
  Emit PromotionCandidateRecord with full lineage.
  2-of-2 co-signature: survivor_model + human_promoter.
  Record AdapterLegitimacyRecord with 9/9 satisfied.
```

**Group controls into adapter families** (scalar config, list membership, count-based, presence/absence, policy bindings, string/banner checks) and promote one family at a time. This prevents drowning in bespoke per-control work.

---

# Part VII — Export Projection Laws

The export (web app, HTML, dashboard, API) is **only a governed projection of factory artifacts**. It has **zero semantic authority**.

### EL-1 — No Export Truth Authority

The export may not originate canonical truth values. If no promoted factory artifact exists, the export must show: `projected_unresolved`, `under_maturation`, `out_of_scope`, `advisory_only`, or `error`. Nothing stronger.

### Export Projection Gates (EP-1 through EP-12)

| Gate | Rule | Fail means |
| ---- | ---- | ---------- |
| EP-1 | No independent judgment | Export computes no pass/fail/open from raw evidence or local rules |
| EP-2 | No DSL interpretation | Export does not parse criteria operators (`<=`, `>=`, `AND`, `OR`) |
| EP-3 | Unresolved preservation | Controls without promoted artifacts render as `projected_unresolved` |
| EP-4 | Promotion-only resolution | Only promoted factory artifacts can resolve a control |
| EP-5 | Factory/export equivalence | Export renders exactly what factory produced |
| EP-6 | Scope honesty | Export preserves factory scope limits exactly |
| EP-7 | Provenance preservation | Every rendered result traces to artifact id, judgment refs, evidence refs |
| EP-8 | Advisory/execution separation | Advice is marked advisory-only; execution is distinct |
| EP-9 | No local semantic drift | Browser state controls visibility/sorting/filtering only, never verdicts |
| EP-10 | No role drift | Export does not construct evaluators, witnesses, or promote controls |
| EP-11 | Projected-unresolved semantics | Unresolved includes explanation, factory fixture link, and explicit "no live adapter promoted" |
| EP-12 | No host contamination | Changing host clears all host-scoped truth state |

### Hard Export Thresholds

```
projection_equivalence_rate       == 1.0
unresolved_preservation_rate      == 1.0
scope_fidelity_rate               == 1.0
role_drift_incidents              == 0
frontend_truth_invention_incidents == 0
```

If any fails: `EXPORT_INVALID`. No shipping.

---

# Part VIII — Per-Control Capability Model

Every control carries three independent status fields. The UI renders strictly from these; it never infers capability.

```
semantic_maturity_status:
  factory_validated         — contract DSL evaluated against fixtures
  under_criticism           — open criticism or falsifier

live_adapter_status:
  not_started               — no capture evidence
  capture_only              — real captures exist but no replay/distinction gates
  replay_verified           — replay fidelity 1.0 against captures
  distinction_verified      — DP-1 through DP-10 pass
  promoted                  — full adapter legitimacy 9/9, promotion record exists

export_projection_status:
  projected_unresolved      — no promoted adapter; factory logic may be validated
  advisory_only             — remediation advice available, no live truth
  live_resolved             — promoted adapter, live pullback passed
  blocked                   — hard gate failure or open criticism
  out_of_scope              — control outside declared scope
```

### UI Rendering Rule

| `live_adapter_status` | UI behavior |
| --------------------- | ----------- |
| `promoted` | Allow Validate; show live pass/fail/open with provenance |
| Any other value | Show `projected_unresolved`; show factory fixture evidence; no live validate button |

**No fallback logic. No inference. No "looks compliant."**

---

# Part IX — Web App UI Coalgebra

The web app is itself a coalgebra with typed state, typed events, and pure render adapters over canonical backend bundles. See BUILD_SPEC for full type definitions. The critical rules:

1. All semantic panels render **only** from typed backend bundles (`ValidationViewBundle`, `AdjudicationViewBundle`, etc.)
2. Local UI state controls **only** visibility, sorting, filtering, expansion/collapse, draft inputs
3. No JS/TS module may construct canonical STIG pass/fail/open semantics
4. Host change clears all host-scoped truth state
5. V-ID pinning enforced across all tabs
6. Gate degradation disables execution actions
7. Merge flow is a closed state machine: `edit → verify → merge → save`
8. Stale bundles rejected on host/V-ID change

---

# Part X — Coverage Summary (Required in Product)

The product must always display:

```
67 total controls
N  live-supported (adapter promoted, 9/9 legitimacy)
M  factory-validated / live-adapter pending
0  silently inferred
```

This single summary stops the user from thinking the bridge is complete when it is not.

---

# Part XI — Records Required

| Record | Purpose |
| ------ | ------- |
| `MeasurableBindingRecord` | Maps contract measurable to runtime source path and projection function |
| `LawfulPartitionRecord` | Declares the lawful partition for a measurable |
| `RepresentationEquivalenceRecord` | Declares normalization rules and known equivalent encodings |
| `AtomicPullbackRowRecord` | The irreducible comparison row: required, observed, operator, verdict |
| `FixtureExpectationRecord` | Per-fixture expected outcome |
| `AdapterLegitimacyRecord` | 9-field checklist with references to evidence for each |
| `ExportProjectionGateRecord` | EP-1 through EP-12 pass/fail with metrics |
| `FactoryExportEquivalenceRecord` | Fixture-pack comparison between factory and export |

---

# Part XII — Forbidden Patterns

These are **hard fails**. Any occurrence blocks promotion and shipping.

| Pattern | Detection | Why it kills |
| ------- | --------- | ------------ |
| Per-control `evaluate_vXXXX()` functions | Static lint / regex | Hand-authored evaluators bypass generic engine |
| Inline comparison (`<=`, `>=`) in export | Code review / lint | Export becomes second evaluator |
| Direct `expected == observed` without witness | `c18` test | Pullback bypass |
| Advice rendered as execution | UI test | Advisory/execution collapse |
| `projected_unresolved` rendered as pass/fail | UI test | Unresolved laundering |
| Promotion without 9/9 legitimacy | `AdapterLegitimacyRecord` check | Premature truth claim |
| Export diverging from factory | Equivalence test | Split-brain product |
| Silent scope inflation | Scope test | Fake universality |

---

# Anchor

**The domain coalgebra is the machine that transforms raw evidence into witness-mediated, pullback-tested, distinction-preserving, falsifier-backed, scope-honest truth — and the export is only a governed projection of what that machine has actually promoted. Nothing ships until 9/9 legitimacy is satisfied per adapter family, all 10 distinction-preserving gates pass, and factory/export equivalence is exact. Anything less is `projected_unresolved`.**

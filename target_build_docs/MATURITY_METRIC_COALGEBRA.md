---
INVARIANT — BUILD ORDER LAW (INVIOLABLE)

Projection coalgebra may not exist unless Adapter coalgebra is promoted.

SYSTEM-LEVEL KILL SWITCH:
If adapter families are not promoted, then:
  - Export must not resolve controls
  - UI must not present validation capability
  - Any code attempting evaluation outside kernel = FAIL
---

# ICF Information & Software Engineering Maturity Metric Coalgebra

Version: `1.0.0`
Status: `normative`
Supersedes: `docs/info_maturity_score.md`, `docs/info_maturity_score_v2.md`, `docs/stig_information_maturity_test.md`, `docs/general_information_maturity_test.md`, `docs/robotics_information_maturity_test.md`, `docs/MATURITY_BACKLOG.md`, `docs/BUILD_SPEC.md`, `docs/LIVE_RUN_REPORT.md`

This document is the **sole authoritative specification** for the maturity metric coalgebra that governs whether a product can ship. It defines: what maturity is, how it is measured, what gates block promotion, what the promotion pipeline does, and when the product is client-deliverable.

---

# Part I — Maturity as a Coalgebra

The maturity system is itself a coalgebra. It is not prose about quality; it is a machine with typed state, typed events, and a deterministic step function. The Seven-Part Coalgebra Production Test applies:

## M-C1 — Maturity State

```
X_maturity = {
  per_control_status     : Map<ControlId, ControlMaturityState>
  per_family_status      : Map<AdapterFamilyId, FamilyMaturityState>
  open_criticisms        : Set<CriticismId>
  active_corrections     : Set<CorrectionTaskId>
  promotion_queue        : Queue<PromotionCandidateRecord>
  demotion_log           : Vec<DemotionRecord>
  aggregate_metrics      : AggregateMaturitySnapshot
  shipping_gate_state    : ShippingGateState
}
```

Where:

```
ControlMaturityState = {
  semantic_maturity   : factory_validated | under_criticism
  live_adapter        : not_started | capture_only | replay_verified | distinction_verified | promoted
  export_projection   : projected_unresolved | advisory_only | live_resolved | blocked | out_of_scope
  fixture_coverage    : { present: u8, required: u8, deferred: u8 }
  legitimacy          : { satisfied: u8, total: 9 }
  dp_gates            : { passed: u8, total: 10 }
  open_falsifiers     : u8
  open_criticisms     : u8
}

FamilyMaturityState = {
  family_id           : AdapterFamilyId
  member_controls     : Set<ControlId>
  family_promotion    : not_started | partial | fully_promoted
  family_legitimacy   : { min_satisfied: u8, max_satisfied: u8, total: 9 }
  family_dp_gates     : { min_passed: u8, max_passed: u8, total: 10 }
  blocking_controls   : Set<ControlId>
}

ShippingGateState = {
  all_gates_passed    : bool
  blocking_reasons    : Vec<String>
  last_evaluated      : Timestamp
}
```

## M-C2 — Maturity Observations

```
O_maturity = {
  ControlMaturityUpdate
  FamilyMaturityUpdate
  PromotionGranted
  PromotionRefused
  DemotionIssued
  CorrectionTaskCreated
  CorrectionTaskCompleted
  ShippingGateEvaluation
  AggregateMaturitySnapshot
}
```

## M-C3 — Maturity Events

```
I_maturity = {
  RunFixtureTest(ControlId, FixturePack)
  RunReplayTest(ControlId, AdapterCaptureSet)
  RunDistinctionGate(ControlId, GateId)
  RunLegitimacyCheck(ControlId, CheckId)
  SubmitPromotionCandidate(ControlId)
  IssueCriticism(ControlId, CriticismRecord)
  ResolveCriticism(CriticismId, ResolutionEvidence)
  InjectBreak(ControlId, BreakRecord)
  ApplyFix(ControlId, FixRecord)
  EvaluateShippingGate
}
```

## M-C4 — Maturity Step Function

```
step_maturity : X_maturity × I_maturity → O_maturity* × X_maturity
```

Each event updates the relevant control/family state, re-evaluates gate conditions, and emits observations. The function is deterministic and replayable.

## M-C5 — Maturity Distinction

Two maturity states are distinct if they produce different promotion/demotion/shipping-gate decisions for the same input sequence.

## M-C6 — Maturity Falsifier

The maturity coalgebra is falsified if:
- A product ships with any control below `live_resolved`
- A promotion is granted without 9/9 legitimacy
- A demotion record is lost
- Aggregate metrics disagree with per-control data

## M-C7 — Maturity Scope

The maturity coalgebra applies to the stated domain, platform family, adapter set, and software version. It does not claim universality.

---

# Part II — Hard Gates (10 Gates)

These gates are **binary pass/fail**. Any failure blocks ALL downstream promotion and export. They are evaluated before any maturity metric is computed.

| Gate | Name | Rule | Consequence of Failure |
| ---- | ---- | ---- | --------------------- |
| HG-1 | Pullback Exists | Every claim resolves through a witness-mediated pullback. No direct comparison. | No coalgebra. Full stop. |
| HG-2 | Falsifier Exists | At least one non-vacuous falsifier per control. | Cannot enter maturity scoring. |
| HG-3 | Break-Fix Closure | Break → detect → propose-fix → apply → revalidate loop is closed. | No survivor lineage → no promotion. |
| HG-4 | Scope Declared | Every evaluator, adapter, and witness declares scope axes. | All outputs carry scope warnings. |
| HG-5 | Criticism Durability | Ledger is append-only. Hash chain intact. No deleted criticism records. | Ledger integrity failure → full halt. |
| HG-6 | Deterministic Replay | `step(state, event)` replays identically under frozen inputs/seeds. | Cannot trust any test result. |
| HG-7 | Witness Non-Trust | No witness is inherently trusted. All witnesses earn status via survival. | Trust inflation → false assurance. |
| HG-8 | Evidence Preservation | Raw evidence blobs are content-addressed and tamper-detectable. | Cannot verify any claim. |
| HG-9 | No Direct Alignment | System forbids `expected == observed` without witness mediation. | Pullback bypass → no coalgebra. |
| HG-10 | Governance Exists | Promotion requires explicit authority (machine policy + human sign-off). | Unauthorized promotions. |

---

# Part III — Maturity Metric Stack

These are computed **only after all 10 Hard Gates pass**. They are structured in three tiers with a mandatory loop.

## Gate A — Core Maturity (M1–M8)

The eight metrics that answer: "Is this coalgebra real and tested?"

| ID | Metric | Computation | Threshold |
| -- | ------ | ----------- | --------- |
| M1 | Coalgebra completeness | Fraction of C1–C7 answered with machine-testable artifacts | `1.0` |
| M2 | Falsifier density | Non-vacuous falsifiers executed per control | `≥ 1` per control |
| M3 | Break-fix closure | `{closed loops} / {injected breaks}` | `1.0` |
| M4 | Witness coverage | `{controls with surviving witnesses} / {total controls}` | `1.0` for promoted |
| M5 | Criticism response | `{resolved criticisms} / {total criticisms}` over window | `1.0` for shipping |
| M6 | Survivor lineage depth | Min failure→promotion chain length | `≥ 2` |
| M7 | Replay fidelity | `{deterministic replays} / {total replay runs}` | `1.0` |
| M8 | Scope coverage | `{in-scope tested controls} / {in-scope claimed controls}` | `1.0` for promoted |

## Gate B — Error Correction (E1–E8)

The eight metrics that answer: "Can this system detect and recover from its own mistakes?"

| ID | Metric | Computation | Threshold |
| -- | ------ | ----------- | --------- |
| E1 | Synthesis demotion rate | `{demoted syntheses} / {proposed syntheses}` | `> 0` (proves the gate is active) |
| E2 | False-positive detected | `{false positives caught by criticism} / {total criticisms}` | Tracked, not thresholded |
| E3 | Contradiction detection | Contradictions flagged across claim/witness/evidence levels | `≥ 1` seeded test detected |
| E4 | Optimization regression | Cases where optimization reduced falsifier yield | `0` |
| E5 | Witness retirement rate | Old/inadequate witnesses replaced | `> 0` (proves lifecycle active) |
| E6 | Remediation verification | `{verified remediations} / {total remediations}` | `1.0` for shipping |
| E7 | Demotion completeness | Every demotion traceable to triggering falsifier/criticism | `1.0` |
| E8 | Level-consistency violations | Detected cross-level contradictions | `0` unresolved at ship time |

## Gate C — Anti-Drift (D1–D8)

The eight metrics that answer: "Will this system stay truthful over time?"

| ID | Metric | Computation | Threshold |
| -- | ------ | ----------- | --------- |
| D1 | Semantic drift | Factory/export divergence rate | `0.0` |
| D2 | Role drift | Frontend constructing evaluators/witnesses | `0` incidents |
| D3 | Scope inflation | Controls promoted beyond tested scope | `0` incidents |
| D4 | Distinction collapse | Distinct operational states returning same verdict | `0` incidents |
| D5 | Unresolved laundering | `projected_unresolved` rendered as anything stronger | `0` incidents |
| D6 | Advisory elevation | Advisory remediation rendered as execution | `0` incidents |
| D7 | Trust inflation | Witness trusted without survival history | `0` incidents |
| D8 | Governance bypass | Promotion without required authority | `0` incidents |

---

# Part IV — The Maturity Loop (Run-to-Truth)

This is the operational loop that takes the system from "capture_only" to "client-deliverable." It is not aspirational; it is the required engineering process.

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  FOR EACH adapter_family:                               │
│                                                         │
│    1. CAPTURE real device evidence                      │
│       → store content-addressed                         │
│       → status: capture_only                            │
│                                                         │
│    2. NORMALIZE evidence to atomic measurables          │
│       → write deterministic extractors                  │
│       → declare MeasurableBindingRecord                 │
│                                                         │
│    3. BUILD fixture pack (all 9 classes)                │
│       → each fixture declares expected outcome          │
│       → fixture_coverage: 9/9                           │
│                                                         │
│    4. REPLAY against fixtures                           │
│       → replay_fidelity must equal 1.0                  │
│       → known-bad must fail; known-good must survive    │
│       → status: replay_verified                         │
│                                                         │
│    5. RUN distinction gates DP-1 through DP-10          │
│       → all 10 must pass                                │
│       → status: distinction_verified                    │
│                                                         │
│    6. CHECK legitimacy 9/9                              │
│       → emit AdapterLegitimacyRecord                    │
│       → if <9/9: LOOP BACK to step that failed          │
│                                                         │
│    7. COMPARE factory output to export output           │
│       → projection_equivalence_rate must equal 1.0      │
│       → if diverges: fix export, re-run comparison      │
│                                                         │
│    8. PROMOTE                                           │
│       → emit PromotionCandidateRecord                   │
│       → co-sign: survivor_model + human_promoter        │
│       → emit PromotionRecord                            │
│       → status: promoted                                │
│                                                         │
│    9. EVALUATE shipping gate (Part V)                   │
│       → if blocked: identify blocker, return to step    │
│                                                         │
│  END FOR                                                │
│                                                         │
│  EVALUATE aggregate shipping gate                       │
│  IF all pass: SHIP                                      │
│  ELSE: display coverage summary, blockers, next steps   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Every step records its outcome to the ledger.** Nothing is ephemeral.

---

# Part V — Shipping Gate

The product ships to a client **only** when all of the following hold simultaneously:

## Prerequisites

```
All 10 Hard Gates pass                                    (HG-1 through HG-10)
All 8 Core Maturity metrics at threshold                  (M1–M8)
All 8 Error Correction metrics at threshold               (E1–E8)
All 8 Anti-Drift metrics at threshold                     (D1–D8)
```

## Per-Control Requirements

```
FOR EACH control in_scope:
  IF control.live_adapter != promoted:
    shipping_gate = FAIL
    blocking_reason += "control {id} adapter not promoted"

  IF control.legitimacy.satisfied != 9:
    shipping_gate = FAIL
    blocking_reason += "control {id} legitimacy {sat}/9"

  IF control.dp_gates.passed != 10:
    shipping_gate = FAIL
    blocking_reason += "control {id} DP gates {passed}/10"

  IF control.export_projection != live_resolved AND control.export_projection != out_of_scope:
    shipping_gate = FAIL
    blocking_reason += "control {id} export not resolved"

  IF control.open_criticisms > 0:
    shipping_gate = FAIL
    blocking_reason += "control {id} has open criticisms"

  IF control.open_falsifiers > 0:
    shipping_gate = FAIL
    blocking_reason += "control {id} has open falsifiers"
```

## Aggregate Requirements

```
projection_equivalence_rate       == 1.0
unresolved_preservation_rate      == 1.0
scope_fidelity_rate               == 1.0
role_drift_incidents              == 0
frontend_truth_invention_incidents == 0
```

## Shipping Gate Output

```
ShippingGateEvaluation = {
  pass                   : bool
  timestamp              : Timestamp
  total_controls         : u16
  live_resolved          : u16
  projected_unresolved   : u16
  out_of_scope           : u16
  blocked                : u16
  blocking_reasons       : Vec<String>
  aggregate_metrics      : AggregateMaturitySnapshot
  next_step              : Option<String>
}
```

If `pass == false`, the `next_step` field identifies the **single most impactful** unblocking action (usually: "promote adapter family X — currently blocking Y controls").

---

# Part VI — Adapter Family Strategy

The key engineering insight: controls cluster into **adapter families** that share capture/normalization/evaluation patterns. Promoting one family unblocks many controls.

## Required Family Classification

| Family | Signature | Example Controls |
| ------ | --------- | ---------------- |
| `scalar_config` | Single numeric threshold comparison | `maxhdr`, `inactivity_timeout`, `connection_limit` |
| `list_membership` | Set containment or list match | `ciphersuites`, `allowed_vlans`, `protocol_list` |
| `count_based` | Numeric count against threshold | `connection_mirrors`, `monitor_count` |
| `presence_absence` | Boolean existence of feature/setting | `ssl_enabled`, `hsts_header`, `snat_pool` |
| `policy_binding` | Named policy/profile attached correctly | `http_profile`, `ssl_profile`, `irule_attachment` |
| `string_banner` | Text content matching pattern | `login_banner`, `advisory_text`, `hostname_format` |
| `cert_lifecycle` | Certificate/key properties | `cert_expiry`, `key_length`, `chain_validity` |
| `access_control` | Role/permission/auth settings | `admin_auth`, `session_timeout`, `rbac_config` |
| `network_segment` | VLAN/route/interface configuration | `self_ip`, `route_domain`, `vlan_tagging` |

## Family Promotion Priority

Rank families by `controls_unblocked / effort_to_promote`. Start with the family that unblocks the most controls for the least effort. The shipping gate's `next_step` field should reflect this prioritization.

---

# Part VII — Correction Discipline

When the maturity loop finds a failure, the correction process follows this protocol:

## Correction Task Record

```
CorrectionTaskRecord = {
  id               : CorrectionTaskId
  trigger          : CriticismId | FalsifierId | GateFailId
  category         : distinction_loss | adapter_gap | fixture_missing |
                     replay_failure | export_divergence | scope_inflation |
                     promotion_bypass | unresolved_laundering
  affected_controls : Set<ControlId>
  root_cause        : String
  correction_action : String
  status            : open | in_progress | resolved | verified
  resolution_evidence : Option<EvidenceRef>
}
```

## Correction Priority

```
P0 — Hard gate failure        : Fix immediately. All promotion/export halted.
P1 — Distinction loss         : Fix before any further promotion in affected family.
P2 — Adapter gap              : Part of normal maturity loop.
P3 — Export divergence        : Fix before shipping.
P4 — Scope/coverage           : Track, schedule.
```

## Regression Prevention

Every correction produces a **regression fixture** that is permanently added to the test suite. The fixture must demonstrate the specific failure condition that was corrected. This prevents the same class of failure from recurring silently.

---

# Part VIII — The MaturityGateRecord Schema

Every gate evaluation produces a structured record stored in the ledger:

```json
{
  "schema": "MaturityGateRecord/1.0",
  "timestamp": "ISO-8601",
  "gate_id": "HG-1 | M1 | E1 | D1 | DP-1 | EP-1 | ...",
  "subject_id": "control_id | family_id | system",
  "verdict": "pass | fail | not_evaluated",
  "evidence_refs": ["hash1", "hash2"],
  "value": 0.0,
  "threshold": 1.0,
  "blocking": true,
  "notes": ""
}
```

---

# Part IX — Live Evidence Requirements

For any control that claims `live_resolved`, these six conditions must hold simultaneously:

| ID | Requirement | Meaning |
| -- | ----------- | ------- |
| L1 | Live device evidence | tmsh/REST output from a real device, stored content-addressed |
| L2 | Live normalization | Evidence flows through the declared extraction pipeline |
| L3 | Live pullback | The pullback runs against live-extracted atomic measurable, not fixture |
| L4 | Live witness | A surviving witness mediates the comparison |
| L5 | Live verdict | Pass/fail/open is determined by the factory kernel, not the export |
| L6 | Live provenance | The result carries a complete provenance chain: device → blob → extract → pullback → verdict |

Without all six, the control is `projected_unresolved` regardless of how good the factory logic looks.

---

# Part X — Stop Conditions

The maturity loop terminates when:

```
ALL in-scope controls: live_adapter == promoted
ALL in-scope controls: legitimacy == 9/9
ALL in-scope controls: dp_gates == 10/10
ALL in-scope controls: export_projection == live_resolved OR out_of_scope
ALL in-scope controls: open_criticisms == 0
ALL in-scope controls: open_falsifiers == 0

Aggregate: projection_equivalence_rate == 1.0
Aggregate: unresolved_preservation_rate == 1.0
Aggregate: scope_fidelity_rate == 1.0
Aggregate: role_drift_incidents == 0
Aggregate: frontend_truth_invention_incidents == 0

ShippingGateEvaluation.pass == true
```

Until these hold, the loop continues. There is no timeout, no "good enough" shortcut, and no manual override.

---

# Part XI — What "Fail Safe to a Client" Means

The product is fail-safe when every possible degradation mode renders as honest uncertainty rather than false confidence:

| Degradation | Product behavior |
| ----------- | ---------------- |
| No live adapter | Control shows `projected_unresolved` with factory fixture evidence |
| Adapter capture but no replay | Control shows `capture_only` status, not live truth |
| Replay passes but distinction gates fail | Control shows `replay_verified` but not promoted |
| Open criticism on a promoted control | Control shows `under_criticism`, live validate disabled |
| Open falsifier on a promoted control | Control shows `blocked`, requires investigation |
| Export/factory divergence detected | Export shows `EXPORT_INVALID`, all controls |
| Scope exceeded | Control shows `out_of_scope` with scope boundaries |
| Device unreachable | Control shows `no_live_evidence` |

**In every case, the product shows the user exactly what it knows and exactly what it does not know.** The user never has to guess whether a green checkmark is real.

---

# Part XII — Waste Heat Ratio (WHR)

WHR measures the fraction of engineering effort that does not contribute to maturity progress:

```
WHR = (total_effort - distinction_increasing_effort) / total_effort
```

Track per sprint/cycle. WHR should decrease monotonically. If it increases:
- The correction discipline is generating rework, not progress
- The fixture pack is incomplete, causing repeated failures
- The adapter family classification is wrong, preventing batch promotion

WHR increase triggers a process retrospective, not harder coding.

---

# Anchor

**The maturity metric coalgebra is a typed state machine that tracks every control from `not_started` through `promoted`, evaluates 10 hard gates + 24 metrics + 10 distinction gates + 12 export projection gates, and refuses to ship until every in-scope control is live-resolved or honestly out-of-scope. The system degrades into uncertainty, never into false confidence. The loop runs until the stop conditions hold. There is no shortcut.**

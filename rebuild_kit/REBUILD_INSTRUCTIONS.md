# ICF Rebuild Instructions

Version: `1.0.0`
Purpose: Step-by-step engineering build order for the ICF STIG Expert Critic system.

This kit is designed so that **any competent software agent or engineer** can rebuild the system from scratch, producing a client-deliverable product that does not suffer from the deficiencies of the previous build (partial adapter promotion, export-layer truth invention, "4/9 legitimacy" across most controls).

---

# 1. What This Kit Contains

```
rebuild_kit/
├── REBUILD_INSTRUCTIONS.md       <-- YOU ARE HERE
├── specs/
│   ├── DOMAIN_COALGEBRA.md       -- All domain rules, laws, gates, and constraints
│   └── MATURITY_METRIC_COALGEBRA.md -- All maturity metrics, promotion pipeline, shipping gate
├── domain_data/
│   ├── assertion_contracts.json  -- 67 STIG controls with criteria DSL
│   ├── disa_stigs.json           -- 69 DISA findings (check/fix text)
│   ├── stig_list.csv             -- Canonical 67 V-ID list
│   └── local_policy/             -- Example local policy input
├── evidence/
│   ├── blobstore_live/           -- 41 content-addressed blobs from real F5 BIG-IP
│   ├── live_state/               -- Manifests, preflight, 31 tmsh/REST snapshots
│   └── ledgers_live/             -- Exemplar ledgers from live break/fix and full campaign
├── coalgebra_artifacts/
│   └── stig_expert_critic/       -- 41 files: schemas, falsifier catalog, witness specs, etc.
├── fixtures/
│   └── maturity/                 -- Revision fixtures for maturity metric tests
└── reference_kernel/
    ├── Cargo.toml                -- Rust project (serde + serde_json only)
    ├── rust-toolchain.toml       -- Rust 1.78.0
    ├── src/                      -- 11 modules: working kernel (50+ tests pass)
    └── tests/                    -- 7 integration test files
```

## Relationship between folders

- `specs/` defines **what the system must be** (laws, gates, metrics, stop conditions).
- `domain_data/` defines **what the system evaluates** (67 STIG controls with typed criteria).
- `evidence/` provides **real F5 device captures** that the adapter pipeline must process.
- `coalgebra_artifacts/` provides **schemas and exemplar records** that define the data model.
- `reference_kernel/` is a **working Rust implementation** of the coalgebra kernel. It passes all C1-C20 coalgebra gates and 50+ tests. Use it as reference, not as something to blindly copy.

---

# 2. Architecture Overview

The system has three layers. **Build them in order.** Do not skip ahead.

```
┌─────────────────────────────────────────────┐
│  Layer 3: Export Projection                 │
│  (web app, HTML dashboard, API)             │
│  Zero semantic authority. Renders only       │
│  what Layer 2 has promoted.                  │
├─────────────────────────────────────────────┤
│  Layer 2: Adapter Promotion Pipeline        │
│  Capture → Normalize → Fixture → Replay →   │
│  Distinction Gates → Legitimacy → Promote    │
├─────────────────────────────────────────────┤
│  Layer 1: Coalgebra Kernel                  │
│  State machine, ledger, pullback, step       │
│  function, distinction logic, falsifiers     │
└─────────────────────────────────────────────┘
```

**Layer 1** is the truth engine. It takes state + event and produces observations + next state.
**Layer 2** is the bridge from raw device evidence to promoted adapter families. This is what failed in the previous build.
**Layer 3** is a governed projection. It displays whatever Layer 2 has promoted. It never invents truth.

---

# 3. The Previous Build's Failures (Do Not Repeat These)

The previous build failed because:

1. **Layer 2 was never completed.** The adapter promotion pipeline stopped at "capture_only" for most controls. The system had real captures but never built the full fixture packs, never ran distinction gates, never achieved 9/9 legitimacy.

2. **Layer 3 was built before Layer 2 was done.** The export/web app was constructed while most adapters were still at "capture_only." It then had to display something, so it showed `projected_unresolved` and `4/9 legitimacy` — which is technically honest but useless to a client.

3. **Per-control bespoke evaluators.** Instead of classifying controls into adapter families and building generic evaluators, individual `evaluate_vXXXX()` functions were hand-authored. This is unscalable and fragile.

4. **No fixture packs.** Controls lacked the mandatory 9 fixture classes (good, bad, boundary, disabled, absent, malformed, noisy, out-of-scope, representation variant). Without fixtures, replay and distinction gates cannot run.

5. **Export truth invention.** The HTML export attempted to parse criteria DSL (`<=`, `>=`, `AND`, `OR`) and compute verdicts locally, violating EP-1 and EP-2.

---

# 4. Build Order (7 Phases — Strict Sequence)

## Phase 1: Coalgebra Kernel

**Goal:** A deterministic state machine that passes C1-C7 of the Coalgebra Production Test.

**Input files:**
- `specs/DOMAIN_COALGEBRA.md` Part I (Seven-Part Test)
- `coalgebra_artifacts/stig_expert_critic/StateSchema.json`
- `coalgebra_artifacts/stig_expert_critic/EventSchema.json`
- `coalgebra_artifacts/stig_expert_critic/ObservationSchema.json`
- `reference_kernel/src/model.rs` (reference implementation of `step`)
- `reference_kernel/src/ledger.rs` (reference implementation of append-only ledger)

**Build:**
1. Define state type `X` per `specs/DOMAIN_COALGEBRA.md` §C1.
2. Define observation type `O` per §C2.
3. Define event type `I` per §C3.
4. Implement `step : X × I → O* × X` per §C4. Must be deterministic.
5. Implement append-only JSONL ledger with hash chaining.
6. Implement `verify_ledger` that replays and checks hash chain integrity.
7. Write tests: deterministic replay, hash chain verification, behavioral distinction (§C5).

**Exit gate:** `step` replays identically under frozen inputs. Ledger verification passes. At least one falsifier exists per §C6. Scope is declared per §C7.

**Reference:** `reference_kernel/src/model.rs` contains a working `step` function. `reference_kernel/tests/coalgebra_gate.rs` shows how to test it.

---

## Phase 2: STIG Catalog Integration

**Goal:** Parse all 67 controls from `assertion_contracts.json` into typed measurable bindings.

**Input files:**
- `domain_data/assertion_contracts.json` (67 contracts with criteria DSL)
- `domain_data/disa_stigs.json` (DISA narrative text)
- `domain_data/stig_list.csv` (canonical V-ID list)
- `specs/DOMAIN_COALGEBRA.md` Part III (DP-1 through DP-10)
- `reference_kernel/src/stig_catalog.rs` (reference catalog builder)
- `reference_kernel/src/distinction.rs` (reference distinction gates)

**Build:**
1. Parse `assertion_contracts.json` into typed records.
2. For each control, extract: `vuln_id`, `evidence_required`, `criteria` (pass/fail predicates), `validation_method`, `tmsh_commands`, `rest_endpoints`, `runtime_family`.
3. Classify each control into an **adapter family** (see §5 below).
4. For each control, build a `MeasurableBindingRecord`: maps contract measurable ID to runtime source path and atomic value type.
5. For each control, build a `LawfulPartitionRecord`: declares the lawful partition (`{compliant, noncompliant, disabled, absent, malformed, indeterminate}`).
6. Write tests that confirm all 67 V-IDs are parsed, bound, and partitioned.

**Exit gate:** All 67 controls have typed bindings and lawful partitions. No control is unbound.

---

## Phase 3: Adapter Families

**Goal:** Classify all 67 controls into adapter families and build one generic evaluator per family.

The 67 controls split into two `runtime_family` groups: **28 NDM** (network device management) and **39 ALG** (application layer gateway). Within those, controls cluster by criteria pattern:

### Adapter Family Classification

| Family ID | Criteria Pattern | Example Controls | Count (approx) |
| --------- | --------------- | ---------------- | -------------- |
| `scalar_threshold` | `field <= N` or `field >= N` | `sys_httpd_max_clients <= 10`, `auth_password_policy_min_length >= 15` | ~15 |
| `integer_equality` | `field == N` or `field != N` | `auth_user_shared_accounts == 0`, `auth_user_local_account_count == 1` | ~8 |
| `boolean_flag` | `field == true` or `field == 'enabled'` | `sys_sshd_banner == 'enabled'`, `software_signature_verification_enabled == true` | ~10 |
| `count_threshold` | `field_count >= N` | `sys_syslog_remote_server_count >= 2`, `sys_ntp_server_count >= 2` | ~6 |
| `string_match` | `field == 'expected_value'` | `sys_ntp_timezone == 'UTC'`, `auth_source_type == 'tacacs'` | ~5 |
| `compound_boolean` | `A == x AND B == y AND ...` | `sys_daemon_log_*` with multiple log-level fields | ~8 |
| `policy_assessment` | `field_assessment == true` (human/tool judgment) | `auth_remote_role_assignment_appropriate == true` | ~8 |
| `external_evidence` | Evidence comes from outside tmsh/REST | `audit_log_storage_managed`, `software_signature_verification_enabled` | ~7 |

**Build:**
1. Write one generic evaluator function per family. The evaluator takes `(measurable_binding, evidence_map) → AtomicPullbackRow`.
2. Each evaluator extracts the declared field, normalizes representation, and compares via the declared operator.
3. No per-control `evaluate_vXXXX()` functions. If you find yourself writing one, you have the wrong family classification.
4. Write a dispatch function: given a control's family ID and evidence, route to the correct evaluator.
5. Test each evaluator against at least one known-good and one known-bad input per family.

**Exit gate:** All 67 controls route to a family evaluator. No bespoke per-control evaluator exists.

---

## Phase 4: Fixture Packs

**Goal:** Build all 9 fixture classes for every control that has evidence in `evidence/`.

**Input files:**
- `evidence/blobstore_live/` (41 real captures)
- `evidence/live_state/` (31 snapshots)
- `evidence/live_state/full_campaign/manifest.json` (which snapshot maps to which control)
- `specs/DOMAIN_COALGEBRA.md` Part V (9 fixture classes)

**The 9 mandatory fixture classes per control:**

```
1. good_minimal        — minimal compliant state
2. bad_canonical       — canonical noncompliant state
3. bad_representation  — alternate encoding of same bad state
4. boundary_value      — edge of compliant/noncompliant threshold
5. disabled_state      — feature/service disabled
6. absent_state        — field/object missing entirely
7. malformed_state     — corrupted or truncated evidence
8. noisy_evidence      — correct value buried in extraneous data
9. out_of_scope        — platform/version outside declared scope
```

**Build:**
1. For each adapter family, derive fixture templates from real evidence in `evidence/`.
2. For each control, instantiate the 9 fixtures using the template and control-specific values.
3. Each fixture declares the **expected outcome**: `{pass, fail, unresolved, out_of_scope}` with the specific `AtomicPullbackRow` expected.
4. Controls where a fixture class is genuinely not applicable (e.g., `disabled_state` for a control that cannot be disabled) must declare `not_applicable` with a justification string.

**Exit gate:** Every in-scope control has a fixture pack with all 9 classes marked as `present`, `not_applicable`, or `deferred_with_reason`. No unmarked gaps.

---

## Phase 5: Adapter Promotion Pipeline

**Goal:** Run every adapter family through the full promotion pipeline until 9/9 legitimacy.

This is the phase that the previous build never completed. **Do it family by family**, starting with the family that unblocks the most controls.

**For each adapter family:**

```
Step A — CAPTURE
  Real evidence already exists in evidence/blobstore_live/ and evidence/live_state/.
  For rebuild purposes, use the committed captures.
  If new captures are needed later, use the F5 REST/tmsh scripts.

Step B — NORMALIZE
  Run the family evaluator against each capture.
  Confirm it extracts the correct atomic measurable.
  Record MeasurableBindingRecord.

Step C — FIXTURE
  Confirm all 9 fixture classes exist (Phase 4 output).

Step D — REPLAY
  Run the evaluator against ALL fixtures for ALL controls in this family.
  replay_fidelity must equal 1.0 (every replay produces identical output).
  Known-bad fixtures must fail. Known-good fixtures must pass.

Step E — DISTINCTION GATES
  Run DP-1 through DP-10 (specs/DOMAIN_COALGEBRA.md Part III) for each control.
  All 10 must pass.

Step F — EXPORT EQUIVALENCE
  (Defer until Phase 6 builds the export layer.)

Step G — PROMOTE
  Emit PromotionCandidateRecord with full lineage.
  Emit AdapterLegitimacyRecord with 9/9 satisfied.
  Update control status: live_adapter = promoted.
```

**Priority order for families (most controls unblocked first):**

1. `scalar_threshold` (~15 controls) — highest impact
2. `boolean_flag` (~10 controls)
3. `integer_equality` (~8 controls)
4. `compound_boolean` (~8 controls)
5. `policy_assessment` (~8 controls)
6. `external_evidence` (~7 controls)
7. `count_threshold` (~6 controls)
8. `string_match` (~5 controls)

**Exit gate:** Every in-scope control has `live_adapter == promoted` and `legitimacy == 9/9` and `dp_gates == 10/10`.

---

## Phase 6: Export Projection

**Goal:** Build the web app / dashboard / HTML export that renders Layer 2 output.

**Input files:**
- `specs/DOMAIN_COALGEBRA.md` Part VII (Export Projection Laws EP-1 through EP-12)
- `specs/DOMAIN_COALGEBRA.md` Part VIII (Per-Control Capability Model)
- `specs/DOMAIN_COALGEBRA.md` Part IX (Web App UI Coalgebra)

**Build rules (absolute):**

1. The export renders ONLY from typed backend bundles produced by the kernel + promotion pipeline.
2. The export NEVER parses criteria DSL (`<=`, `>=`, `AND`, `OR`).
3. The export NEVER computes pass/fail/open from raw evidence.
4. Controls without a promoted adapter render as `projected_unresolved` with factory fixture evidence and an explanation.
5. Controls with a promoted adapter render live pullback results with full provenance.
6. Local UI state controls ONLY visibility, sorting, filtering, expansion/collapse.
7. Host change clears all host-scoped truth state.
8. V-ID pinning enforced across all tabs.

**Testing:**
- For each control, compare export output to factory output on the same fixture pack.
- `projection_equivalence_rate` must equal `1.0`.
- `unresolved_preservation_rate` must equal `1.0`.
- `role_drift_incidents` must equal `0`.
- `frontend_truth_invention_incidents` must equal `0`.

**Exit gate:** All EP-1 through EP-12 pass. Factory/export equivalence is exact.

**Now go back and run Step F (export equivalence) for every promoted family from Phase 5.**

---

## Phase 7: Maturity Loop and Shipping Gate

**Goal:** Evaluate the full maturity metric stack and confirm the shipping gate passes.

**Input files:**
- `specs/MATURITY_METRIC_COALGEBRA.md` (entire document)

**Build:**
1. Evaluate all 10 Hard Gates (HG-1 through HG-10). All must pass.
2. Compute all 8 Core Maturity metrics (M1-M8). All must meet threshold.
3. Compute all 8 Error Correction metrics (E1-E8). All must meet threshold.
4. Compute all 8 Anti-Drift metrics (D1-D8). All must meet threshold.
5. Evaluate per-control requirements (every in-scope control: promoted, 9/9, 10/10, no open criticisms, no open falsifiers).
6. Evaluate aggregate requirements (projection equivalence, unresolved preservation, scope fidelity, zero drift incidents).
7. Emit `ShippingGateEvaluation` record.

**Exit gate:** `ShippingGateEvaluation.pass == true`. Product is client-deliverable.

---

# 5. Acceptance Criteria (Stop Conditions)

The rebuild is complete when ALL of the following hold simultaneously:

```
FOR EACH in-scope control (67 total):
  live_adapter_status     == promoted
  legitimacy              == 9/9
  dp_gates                == 10/10
  export_projection       == live_resolved  OR  out_of_scope
  open_criticisms         == 0
  open_falsifiers         == 0

AGGREGATE:
  projection_equivalence_rate          == 1.0
  unresolved_preservation_rate         == 1.0
  scope_fidelity_rate                  == 1.0
  role_drift_incidents                 == 0
  frontend_truth_invention_incidents   == 0

  ShippingGateEvaluation.pass          == true
```

---

# 6. Anti-Patterns (Hard Fails)

If you find yourself doing any of these, stop and re-read the specs.

| Anti-Pattern | Why It Kills | Spec Reference |
| ------------ | ------------ | -------------- |
| Writing `evaluate_v266064()` | Per-control bespoke functions bypass the generic family evaluator. You will have 67 fragile functions instead of 8 robust ones. | DOMAIN_COALGEBRA Part XII |
| Putting `<=` or `>=` in the export JS/HTML | Export is computing verdicts. Violates EP-1 and EP-2. | DOMAIN_COALGEBRA Part VII |
| Rendering `projected_unresolved` as anything else | Unresolved laundering. The user sees fake confidence. | DOMAIN_COALGEBRA Part VII, EP-5 |
| Skipping fixture classes | Without all 9 classes, you cannot run distinction gates. Without distinction gates, you cannot reach 9/9 legitimacy. | DOMAIN_COALGEBRA Part V |
| Building Layer 3 before Layer 2 is done | You will build an export that shows `projected_unresolved` everywhere because no adapters are promoted. This is exactly what happened before. | This document §3 |
| Direct `expected == observed` comparison | Pullback bypass. All comparisons go through witnesses. | DOMAIN_COALGEBRA Part II, P1 |
| Promoting without 9/9 legitimacy | Premature truth claim. The product will show partial legitimacy. | DOMAIN_COALGEBRA Part IV |
| Skipping replay after fixture changes | Replay fidelity must be 1.0. If you change a fixture, re-run replay. | MATURITY_METRIC_COALGEBRA Part III, M7 |

---

# 7. Family-First Strategy

The single most important engineering insight: **promote by family, not by control.**

67 controls promoted individually = 67 × (capture + normalize + 9 fixtures + replay + 10 DP gates + legitimacy check) = unmanageable.

8 adapter families promoted generically = 8 × (generic evaluator + family fixture template + family replay harness + family DP gate runner) = manageable.

Each family promotion unblocks all member controls simultaneously. The family with the most members (`scalar_threshold`, ~15 controls) should be promoted first because it has the highest impact-to-effort ratio.

When a family is promoted:
1. All member controls inherit the family evaluator.
2. Per-control fixtures still exist (they use control-specific values) but the evaluator is shared.
3. Replay runs across all member controls with one harness invocation.
4. DP gates run across all member controls with one gate runner invocation.
5. Legitimacy is checked once per family, not once per control.

---

# 8. File Reference Quick Guide

| When you need... | Look in... |
| ---------------- | ---------- |
| The rules and laws | `specs/DOMAIN_COALGEBRA.md` |
| The maturity metrics and shipping gate | `specs/MATURITY_METRIC_COALGEBRA.md` |
| A control's criteria DSL | `domain_data/assertion_contracts.json` → contract.criteria |
| A control's check/fix narrative | `domain_data/disa_stigs.json` → findings[V-ID] |
| The canonical V-ID list | `domain_data/stig_list.csv` |
| Real F5 evidence blobs | `evidence/blobstore_live/sha256/XX/...` |
| Live tmsh/REST snapshots | `evidence/live_state/full_campaign/snapshots/` |
| Live campaign manifest | `evidence/live_state/full_campaign/manifest.json` |
| Live break/fix manifest | `evidence/live_state/manifest.json` |
| F5 preflight data | `evidence/live_state/preflight.json` |
| Exemplar ledger format | `evidence/ledgers_live/break_fix.jsonl` |
| State schema | `coalgebra_artifacts/stig_expert_critic/StateSchema.json` |
| Event schema | `coalgebra_artifacts/stig_expert_critic/EventSchema.json` |
| Observation schema | `coalgebra_artifacts/stig_expert_critic/ObservationSchema.json` |
| Witness spec | `coalgebra_artifacts/stig_expert_critic/WitnessSpec.json` |
| Falsifier catalog | `coalgebra_artifacts/stig_expert_critic/FalsifierCatalog.md` |
| Promotion policy | `coalgebra_artifacts/stig_expert_critic/PromotionPolicy.md` |
| Governance rules | `coalgebra_artifacts/stig_expert_critic/Governance.md` |
| Scope record | `coalgebra_artifacts/stig_expert_critic/ScopeRecord.json` |
| Working kernel code | `reference_kernel/src/` |
| Working test suite | `reference_kernel/tests/` |
| Rust dependencies | `reference_kernel/Cargo.toml` (serde + serde_json only) |

---

# 9. What "Done" Looks Like

When the rebuild is complete, the product will:

1. Show **67 controls** with live-resolved or honestly out-of-scope status.
2. Show **9/9 legitimacy** for every in-scope adapter.
3. Show **10/10 distinction-preserving gates** for every in-scope control.
4. Show a **coverage summary**: `N live-supported, M out-of-scope, 0 silently inferred`.
5. Allow **live validation** against a real F5 device with full provenance chain.
6. **Degrade into honest uncertainty** when anything is missing (no adapter = `projected_unresolved`, not fake green).
7. Pass the **shipping gate** with `ShippingGateEvaluation.pass == true`.

The user will never have to guess whether a checkmark is real.



# Export-Projection Test Profile v1

## 1. Purpose

The export-projection profile answers one question:

## **Is this export layer still only a governed projection of factory artifacts?**

It must fail if the export:

* invents judgments
* interprets the DSL
* evaluates criteria independently
* widens scope
* collapses unresolved into apparent truth
* diverges from factory output

---

# 2. Subject under test

This profile is run against any **projection-layer artifact**, including:

* web app
* HTML report
* dashboard
* exported JSON bundle
* CLI presentation layer
* printable report
* API response adapter

It is **not** run against the factory evaluator itself.
That remains under **Distinction-Preserving Maturity Test v2**.

---

# 3. Export status classes

The export must classify every rendered state as one of:

* `PROJECTED_RESOLVED`
* `PROJECTED_UNRESOLVED`
* `PROJECTED_ADVISORY`
* `PROJECTED_ERROR`
* `PROJECTED_OUT_OF_SCOPE`

It may **not** emit:

* `PASS`
* `FAIL`
* `OPEN`
* `NOT_A_FINDING`

unless those are directly projected from promoted factory artifacts.

---

# 4. Hard law

## EL-1 — No export truth authority

The export may not originate canonical truth values.

If no promoted factory artifact exists, the export must show:

* unresolved
* under maturation
* out of scope
* advisory only
* error

and nothing stronger.

---

# 5. Export-Projection gates

## EP1 — No frontend/export judgment authority

**Question:** Does the export originate canonical pass/fail/open semantics?

Pass only if:

* every resolved display state is traceable to a promoted factory judgment artifact
* export code contains no independent judgment engine

Fail if:

* export computes pass/fail/open/not_a_finding from raw evidence or local rules

---

## EP2 — No DSL interpretation in export

**Question:** Does the export evaluate the criteria DSL?

Pass only if:

* export treats DSL as display metadata only, or does not handle it at all
* all evaluation was already performed in factory artifacts

Fail if:

* export parses operators like `<=`, `>=`, `==`, `AND`, `OR`, `org_defined_value`
* export binds evidence fields to criteria itself

---

## EP3 — No unresolved collapse

**Question:** Does the export preserve unresolved when factory maturity is absent?

Pass only if:

* controls without promoted artifacts render as unresolved / under maturation / out of scope

Fail if:

* export replaces unresolved with inferred “looks compliant” or equivalent

---

## EP4 — Promotion-only resolution

**Question:** Can a control render as resolved without a promoted factory artifact?

Pass only if:

* every resolved display links to:

  * promoted judgment record
  * source evidence bundle
  * scope
  * falsifier or criticism path

Fail if:

* export resolves from unpromoted or provisional records

---

## EP5 — Factory/export equivalence

**Question:** Does the export render the same canonical result the factory produced?

Pass only if:

* verdict class matches
* atomic pullback rows match
* unresolved classes match
* scope warnings match
* advisory-only flags match

Fail if:

* export reshapes or simplifies result semantics

---

## EP6 — Scope honesty

**Question:** Does the export preserve factory scope limits?

Pass only if:

* displayed result includes scope from factory artifact
* out-of-scope artifacts remain out of scope

Fail if:

* export implies broader applicability than factory proved

---

## EP7 — Provenance preservation

**Question:** Can the user trace the rendered result back to factory artifacts?

Pass only if:

* every resolved or advisory display includes:

  * artifact id
  * source judgment/pullback refs
  * evidence refs
  * scope
  * promotion status

Fail if:

* display is detached from provenance

---

## EP8 — Advisory/execution separation

**Question:** Does the export preserve the distinction between advice and truth, recommendation and execution?

Pass only if:

* advisory outputs are marked advisory-only
* execution state is distinct
* post-fix truth requires new factory validation artifact

Fail if:

* advice appears equivalent to completed remediation

---

## EP9 — No local semantic state drift

**Question:** Can local UI/export state become semantically authoritative?

Pass only if:

* local state controls only:

  * visibility
  * sorting
  * filtering
  * tab selection
  * expansion/collapse
  * pending inputs

Fail if:

* local state controls:

  * canonical verdict
  * lawful partition
  * scope
  * evidence interpretation

---

## EP10 — No role drift

**Question:** Has the export become a second constructor?

Pass only if:

* export does not:

  * construct evaluators
  * construct witnesses
  * synthesize lawful partitions
  * promote controls
  * emit truth-bearing pullback judgments

Fail if:

* any of those are present

---

# 6. Required export metrics

These are smaller than the full maturity stack.

| Metric                               | Meaning                                                                   |
| ------------------------------------ | ------------------------------------------------------------------------- |
| `projection_traceability_rate`       | fraction of rendered results with complete provenance links               |
| `projection_equivalence_rate`        | fraction of export outputs exactly matching factory outputs               |
| `unresolved_preservation_rate`       | fraction of unresolved factory states still unresolved in export          |
| `advisory_honesty_rate`              | fraction of advisory artifacts correctly marked non-authoritative         |
| `scope_fidelity_rate`                | fraction of rendered results preserving factory scope exactly             |
| `role_drift_incidents`               | count of export behaviors that constitute evaluation/adapter construction |
| `frontend_truth_invention_incidents` | count of independent truth computations in export                         |

---

# 7. Export thresholds

## Hard thresholds

These must hold:

```text
projection_equivalence_rate == 1.0
unresolved_preservation_rate == 1.0
scope_fidelity_rate == 1.0
role_drift_incidents == 0
frontend_truth_invention_incidents == 0
```

If any fail:

* export status = `EXPORT_INVALID`

## Soft thresholds

These should be high, but can be training targets:

```text
projection_traceability_rate >= 0.95
advisory_honesty_rate == 1.0
```

---

# 8. Export pass/fail table

| ID   | Gate                       | What it checks                        | Pass condition                                              | Fail means                         |
| ---- | -------------------------- | ------------------------------------- | ----------------------------------------------------------- | ---------------------------------- |
| EP1  | No judgment authority      | export does not originate truth       | all resolved states sourced from promoted factory artifacts | export is a second judge           |
| EP2  | No DSL interpretation      | export does not evaluate contract DSL | no DSL evaluator in export path                             | export is a second evaluator       |
| EP3  | Unresolved preservation    | immature controls stay unresolved     | unresolved preservation rate = 1.0                          | export launders uncertainty        |
| EP4  | Promotion-only resolution  | only promoted artifacts resolve       | every resolved display traces to promoted record            | export resolves provisional states |
| EP5  | Factory/export equivalence | rendered semantics match factory      | projection equivalence rate = 1.0                           | export diverges from factory       |
| EP6  | Scope honesty              | export preserves scope exactly        | scope fidelity rate = 1.0                                   | export widens claims               |
| EP7  | Provenance preservation    | displayed result is traceable         | traceability rate >= 0.95                                   | display detached from evidence     |
| EP8  | Advisory separation        | advice is not truth/execution         | advisory honesty rate = 1.0                                 | advice collapse                    |
| EP9  | No local semantic drift    | local state is cosmetic only          | zero truth-affecting local state authority                  | UI invents semantics               |
| EP10 | No role drift              | export remains projection only        | role drift incidents = 0                                    | export became a constructor        |

---

# 9. Export stop states

| Status                     | Meaning                                                            |
| -------------------------- | ------------------------------------------------------------------ |
| `EXPORT_VALID`             | all hard export gates pass                                         |
| `EXPORT_TRAINING`          | traceability/projection quality improving, but not yet shippable   |
| `EXPORT_INVALID`           | one or more hard export gates failed                               |
| `EXPORT_ROLE_DRIFT`        | export has become evaluator/constructor                            |
| `EXPORT_REDESIGN_REQUIRED` | export architecture must be changed to restore projection boundary |

---

# 10. Export loop

Use this if you want the export checked continuously.

```text
loop:
    measure export metrics
    run EP1–EP10

    if any hard export threshold fails:
        status = EXPORT_INVALID
        if role drift present:
            status = EXPORT_ROLE_DRIFT
        generate corrective action
        continue

    if provenance/traceability below target:
        status = EXPORT_TRAINING
        improve projection bundles / references
        continue

    status = EXPORT_VALID
    stop
```

---

# 11. Corrective actions

If the profile fails, actions should be chosen from:

* remove local judgment code
* remove DSL parsing from export
* add missing provenance fields to export bundle
* force unresolved rendering for unpromoted controls
* align export bundle rendering with factory schema
* add promotion-status check before resolution
* add scope note rendering
* split advisory and execution components
* quarantine role-drift code path

---

# 12. Minimal `ExportProjectionGateRecord`

```json
{
  "record_type": "ExportProjectionGateRecord",
  "schema_version": "1.0.0",
  "record_id": "string",
  "subject_ref": {
    "subject_type": "web_app|report|dashboard|export_bundle|api_projection",
    "subject_id": "string",
    "version": "string"
  },
  "status": "EXPORT_VALID|EXPORT_TRAINING|EXPORT_INVALID|EXPORT_ROLE_DRIFT|EXPORT_REDESIGN_REQUIRED",
  "gates": {
    "ep1_no_judgment_authority_pass": true,
    "ep2_no_dsl_interpretation_pass": true,
    "ep3_unresolved_preservation_pass": true,
    "ep4_promotion_only_resolution_pass": true,
    "ep5_factory_export_equivalence_pass": true,
    "ep6_scope_honesty_pass": true,
    "ep7_provenance_preservation_pass": true,
    "ep8_advisory_separation_pass": true,
    "ep9_no_local_semantic_drift_pass": true,
    "ep10_no_role_drift_pass": true
  },
  "metrics": {
    "projection_traceability_rate": 1.0,
    "projection_equivalence_rate": 1.0,
    "unresolved_preservation_rate": 1.0,
    "advisory_honesty_rate": 1.0,
    "scope_fidelity_rate": 1.0,
    "role_drift_incidents": 0,
    "frontend_truth_invention_incidents": 0
  },
  "blocking_reasons": [],
  "next_action": {
    "action_type": "remove_local_judgment_code|restore_unresolved|add_provenance|restore_scope|split_advisory_execution|stop",
    "rationale": "string"
  }
}
```

---

# 13. Short anchor

**The export-projection test profile proves that the export is only a governed projection of factory maturity. It passes only if it preserves unresolved honesty, provenance, scope, advisory boundaries, and exact factory equivalence—while doing zero independent evaluation, zero DSL interpretation, and zero truth invention.**

To prove the web export was **not vibe coded**, you need tests that show it is a **governed projection** of factory artifacts and **not an independent source of truth**.

The right test suite is not “does the page look right?” It is:

## **Can the export be shown to have no semantic authority of its own, while preserving scope, provenance, unresolved honesty, and exact factory equivalence?**

That means a dedicated **Export-Projection Proof Suite**.

---

# Export-Projection Proof Suite

## 1. No independent judgment test

**Claim to prove:** the export does not originate canonical truth.

### Test

Search/static-check the export codebase for:

* per-control evaluator functions
* criteria comparison logic
* direct PASS/FAIL/OPEN derivation from raw evidence
* DSL interpretation in the web/export layer

### Pass condition

No code path in export computes canonical truth from:

* raw evidence
* criteria DSL
* local heuristics

### Fail condition

Any code in export does things like:

* `if value <= 300: status = ...`
* `evaluate_v266095(...)`
* parsing operators like `<=`, `>=`, `AND`, `OR`

This is the most important anti-vibe test. It proves the export is not secretly a second factory. Your own correction already points here: the export should not interpret DSL or hand-author evaluators; it should remain a projection layer. 

---

## 2. Unresolved honesty test

**Claim to prove:** the export does not fake completeness.

### Test

For controls without promoted live adapters:

* request live validation/export rendering
* inspect returned status and UI state

### Pass condition

Every such control renders:

* `projected_unresolved`
* or equivalent clearly non-truth-bearing state

and does **not** render:

* `not_a_finding`
* `open`
* `pass`
* `fail`

### Fail condition

Any non-promoted control appears resolved.

This is exactly the distinction you recovered with `projected_unresolved` versus `insufficient_evidence`, and it is central to proving the export is honest rather than vibe-coded. 

---

## 3. Promotion-only resolution test

**Claim to prove:** only promoted factory/live artifacts can resolve in the export.

### Test

For each control rendered as resolved:

* trace to promotion status
* trace to promoted factory judgment/live adapter artifact

### Pass condition

Every resolved state has:

* promoted factory artifact ref
* scope
* provenance
* evidence/pullback/judgment lineage

### Fail condition

Any resolved export state lacks promoted backing.

This proves the export is rendering maturity, not inventing it.

---

## 4. Factory/export equivalence test

**Claim to prove:** the export says exactly what the factory says.

### Test

Run the same promoted controls through:

* factory output
* export bundle / API / rendered status

Compare:

* status class
* atomic pullback rows
* unresolved classes
* scope notes
* advisory flags

### Pass condition

Exact equivalence.

### Fail condition

Any mismatch:

* different verdict
* omitted unresolved
* dropped scope warning
* simplified status
* altered advisory marker

Your report already identifies factory/export mismatch as a blocking defect class and makes production maturity contingent on stronger equivalence discipline.

---

## 5. Bundle-shape and provenance test

**Claim to prove:** the export carries substrate, not detached form.

### Test

Inspect every exported/rendered semantic bundle.

### Required fields

At minimum:

* artifact/bundle id
* control/V-ID
* host/scope
* promotion status
* source judgment or pullback refs
* evidence refs
* falsifier or criticism refs
* advisory-only flag where relevant

### Pass condition

All required provenance fields present and usable.

### Fail condition

A rendered “result” exists without traceable origin.

This proves the export artifact is a governed bundle, not dead detached output.

---

## 6. Scope fidelity test

**Claim to prove:** the export does not widen claims.

### Test

For each rendered result:

* compare displayed scope with factory/source scope
* test out-of-scope fixtures/hosts/versions

### Pass condition

Export preserves exact scope and renders out-of-scope honestly.

### Fail condition

Export implies broader applicability than the factory proved.

This addresses one of the most common vibe-coding pathologies: silent generalization.

---

## 7. Advisory/execution separation test

**Claim to prove:** the export preserves the distinction between advice and applied truth.

### Test

Check all remediation/export paths.

### Pass condition

* advice is marked advisory-only
* execution is separate
* no advice text flips compliance state
* post-fix truth requires a new validation artifact

### Fail condition

Advice appears equivalent to completed remediation.

The HTML you provided already tries to preserve this distinction between advisory REST guidance and executable TMSH/merge flows. That should be enforced by tests, not trusted by layout. 

---

## 8. No local semantic drift test

**Claim to prove:** browser/UI state is cosmetic, not authoritative.

### Test

Manipulate:

* selected tab
* host switch
* stale bundle in memory
* local form values
* cached rows

### Pass condition

Local UI state can only affect:

* visibility
* sorting
* filtering
* expansion/collapse
* draft input

It cannot affect:

* canonical verdict
* scope
* evidence interpretation
* adjudication truth

### Fail condition

Changing local state changes canonical semantics.

This is essential for proving the web app is not vibe-coded theater.

---

## 9. Host contamination reset test

**Claim to prove:** the export does not smear one substrate over another.

### Test

Validate on host A, then switch to host B.

### Pass condition

* old statuses cleared/reset
* old evidence/adjudication views cleared
* merge/query state reset as appropriate
* no host A truth remains active for host B

### Fail condition

Any cross-host truth bleed.

Your HTML already contains reset behavior for host change; proving it by test helps show the page is governed rather than improvised. 

---

## 10. No direct comparison / no frontend evaluator test

**Claim to prove:** the web export never performs the pullback itself.

### Test

Forbid in export/UI code:

* expected-vs-observed comparison logic
* field extraction from raw tmsh/rest for canonical judgment
* local assembly of atomic pullback rows from raw payload

### Pass condition

The export only renders factory/live-adapter-produced atomic rows and statuses.

### Fail condition

The export reconstructs or evaluates pullback truth.

This is the cleanest way to prove it is projection, not second implementation.

---

## 11. Projected-unresolved semantics test

**Claim to prove:** unresolved is the lawful projection of missing live maturity, not a bug mask.

### Test

For a non-promoted control:

* inspect returned row set
* inspect status reason
* inspect linked fixture evidence

### Pass condition

Export returns:

* `projected_unresolved`
* clear explanation that factory fixture logic is validated
* explicit statement that no live capture adapter is promoted
* link/pointer to factory fixture evidence bundle

### Fail condition

It collapses into `insufficient_evidence` or a fake resolved verdict.

This is directly aligned with your recent fix and is one of the strongest proofs the export is now architecturally honest. 

---

## 12. Role-drift test

**Claim to prove:** the export has not become a second constructor.

### Test

Check whether export code:

* constructs evaluators
* constructs witnesses
* parses DSL into semantics
* promotes controls
* synthesizes lawful partitions

### Pass condition

None of those roles exist in export.

### Fail condition

Any of them do.

This is the final anti-vibe proof.

---

# Minimal pass/fail table

Use this as the review artifact:

| ID   | Test                           | Pass proves                            |
| ---- | ------------------------------ | -------------------------------------- |
| EP1  | No independent judgment        | export is not a judge                  |
| EP2  | Unresolved honesty             | export does not fake maturity          |
| EP3  | Promotion-only resolution      | export renders only matured truth      |
| EP4  | Factory/export equivalence     | export matches factory semantics       |
| EP5  | Provenance completeness        | export artifacts carry substrate       |
| EP6  | Scope fidelity                 | export does not overclaim              |
| EP7  | Advisory/execution separation  | export preserves distinctions          |
| EP8  | No local semantic drift        | UI state is cosmetic only              |
| EP9  | Host contamination reset       | substrate boundaries preserved         |
| EP10 | No direct comparison           | export does not perform pullback       |
| EP11 | Projected-unresolved semantics | unresolved is honest and specific      |
| EP12 | Role drift                     | export has not become a second factory |

---

# What would count as proof

To say the export was **not vibe coded**, I would require:

* all EP1–EP12 pass
* `projection_equivalence_rate == 1.0`
* `unresolved_preservation_rate == 1.0`
* `scope_fidelity_rate == 1.0`
* `frontend_truth_invention_incidents == 0`
* `role_drift_incidents == 0`

If those hold, you have a strong case that the export is a governed projection rather than a vibe-coded counterfeit.

---

# Short answer

The tests that prove the web export was not vibe coded are the ones that prove it has **no semantic authority of its own**: it does not judge, does not interpret DSL, does not resolve unpromoted controls, does not widen scope, does not collapse advisory into execution, and does not diverge from factory artifacts. If it passes those export-projection gates, then it is behaving as a lawful renderer of factory maturity rather than as improvised application logic.


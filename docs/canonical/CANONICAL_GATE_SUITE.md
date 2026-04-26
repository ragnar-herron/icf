# Canonical Gate Suite

## Status

STATUS: CANONICAL GATE AUTHORITY

Every gate is blocking. A later phase cannot proceed unless all prior required gates have passed and emitted their records.

## Status Vocabulary

Use these statuses exactly:

- `PROJECTED_UNRESOLVED`
- `INSUFFICIENT_EVIDENCE`
- `BLOCKED_EXTERNAL`
- `PROMOTED`
- `DEMOTED`
- `REDESIGN_REQUIRED`
- `DELIVERABLE_SUPPORTED_ONLY`
- `DELIVERABLE_WITH_DECLARED_BOUNDARIES`

## G0 Build-Order Gate

Purpose: prevent phase skipping and role drift.

Inputs:

- `docs/canonical/CANONICAL_BUILD_ORDER.md`
- latest gate records
- source document index

Required records:

- SourceInputInventory
- BuildOrderGateRecord

Pass condition:

- every phase has its predecessor artifact
- no layer starts before the required predecessor gate passes
- source/evidence/backlog documents are not treated as build authority

Fail condition:

- a phase is built from prose plans without the required artifact
- export/web_app starts before adapter promotion gates

Blocking status: `REDESIGN_REQUIRED`

Proof commands/tests:

- inspect generated artifact chain
- verify `docs/canonical/SOURCE_DOCUMENT_INDEX.md` classifications

## G1 General Coalgebra Gate

Purpose: prove the general coalgebra truth engine exists as executable construction, not prose.

Inputs:

- L1 coalgebra tests
- kernel ledger/witness artifacts
- `BUILD_SPEC.md`

Required records:

- KernelGateRecord
- MaturityGateRecord

Pass condition:

- carrier, observables, transition/event structure, witness, replay, and ledger rules are implemented
- replay fidelity is 1.0 on promoted kernel paths

Fail condition:

- any construction exists only as narrative
- record/witness chain cannot be replayed

Blocking status: `REDESIGN_REQUIRED`

Proof commands/tests:

- `scripts/check.ps1`
- `icf coalgebra report`
- kernel-specific replay tests where present

## G2 STIG Distinction Gate

Purpose: prove STIG source distinctions are preserved in catalog/contract semantics.

Inputs:

- `docs/assertion_contracts.json`
- `docs/disa_stigs.json`
- `docs/distinction_preserving_test.md`

Required records:

- DistinctionCatalogRecord
- MeasurableBindingRecord
- LawfulPartitionRecord

Pass condition:

- each control has a lawful contract
- evidence-required fields map to measurable bindings
- not-a-finding/open/unresolved distinctions are explicit

Fail condition:

- criteria are ambiguous
- a control collapses external/manual evidence into appliance evidence
- source identifiers cannot be traced

Blocking status: `INSUFFICIENT_EVIDENCE` or `REDESIGN_REQUIRED`

Proof commands/tests:

- catalog verification commands cited by STIG coalgebra docs
- contract schema validation

## G3 Distinction-Preserving Maturity Gate

Purpose: prove the catalog and adapter model preserve distinctions under fixtures and pullbacks.

Inputs:

- maturity score docs
- distinction-preserving tests
- fixture records

Required records:

- AtomicPullbackRowRecord
- FixtureExpectationRecord
- MaturityGateRecord

Pass condition:

- atomic pullback rows are one measurable per row
- known-good and known-bad fixtures produce expected verdicts
- distinction loss rate is 0
- replay fidelity is 1.0 for promoted paths

Fail condition:

- criteria DSL, UI, or export code performs a second evaluation
- unresolved evidence becomes pass/open without a promoted adapter

Blocking status: `DEMOTED` or `REDESIGN_REQUIRED`

Proof commands/tests:

- `python -m bridge.promote_all`
- fixture suite outputs in `bridge/LegitimacyRecords.json`

## G4 Live Adapter Maturity Gate

Purpose: promote live adapter families only when runtime observation is lawful.

Inputs:

- `bridge/ExportBundle.json`
- `bridge/LegitimacyRecords.json`
- live adapter promotion docs

Required records:

- LiveAdapterPromotionBundle
- LiveAdapterPromotionPortfolio

Pass condition:

- each promoted control has 9/9 legitimacy and 10/10 DP gates
- each family lists supported controls and blocked controls
- no unsupported control is exposed as live-supported

Fail condition:

- adapter lacks fixture evidence
- family status is inferred from coverage rather than promotion records

Blocking status: `DEMOTED`, `BLOCKED_EXTERNAL`, or `REDESIGN_REQUIRED`

Proof commands/tests:

- `python -m bridge.promote_all`
- expected current bridge posture: 60 promoted, 7 projected unresolved

## G5 Live Break/Fix Regression Gate

Purpose: prove live behavior under real appliance evidence and classify blockers honestly.

Inputs:

- live run report
- external evidence packages
- promotion portfolio

Required records:

- LiveRegressionEvidenceBundle
- ExternalEvidencePackage
- BackupCombinedMeasurable where applicable

Pass condition:

- live pass/open/blocked-external dispositions are recorded
- real findings remain open
- external evidence blockers remain blocked until evidence is supplied

Fail condition:

- live failures are relabeled as unresolved to improve metrics
- blocked external evidence is treated as appliance evidence

Blocking status: `BLOCKED_EXTERNAL`, `INSUFFICIENT_EVIDENCE`, or `DEMOTED`

Proof commands/tests:

- live campaign verifier scripts
- regression records cited by `docs/LIVE_RUN_REPORT.md`

## G6 Export Projection Gate

Purpose: prove export/web_app preserves factory truth and does not invent verdicts.

Inputs:

- `bridge/ExportBundle.json`
- `bridge/ProjectionBundle.json`
- export HTML/web_app artifacts

Required records:

- ExportProjectionGateRecord

Pass condition:

- projection equivalence rate is 1.0
- unresolved preservation rate is 1.0
- frontend truth invention incidents equal 0
- role drift incidents equal 0
- live tool behavior is backed by promoted backend paths, not client-side semantics

Fail condition:

- JS or UI parses criteria DSL as a truth engine
- projection-only wrapper is mistaken for the live tool
- `PROJECTED_UNRESOLVED` renders as validated pass/open

Blocking status: `PROJECTED_UNRESOLVED` or `REDESIGN_REQUIRED`

Proof commands/tests:

- `python -m bridge.verify_ep_gates`
- `python -m bridge.verify_packaged_export`

## G7 Client Deliverability Gate

Purpose: ensure the client bundle claim does not exceed supported evidence.

Inputs:

- export projection gate record
- client deliverability gate docs
- release checklist/posture

Required records:

- ClientDeliverabilityGateRecord
- WasteAccountingRecord

Pass condition:

- client status is `DELIVERABLE_SUPPORTED_ONLY` or `DELIVERABLE_WITH_DECLARED_BOUNDARIES`
- supported controls/families are declared
- blocked external/manual/out-of-scope items are disclosed

Fail condition:

- bundle claims full live STIG product without all gates
- release notes hide open findings or external blockers

Blocking status: `DELIVERABLE_WITH_DECLARED_BOUNDARIES` or `REDESIGN_REQUIRED`

Proof commands/tests:

- `scripts/verify_stig_export.ps1`
- packaging smoke tests
- client deliverability record validation

## G8 Release Gate

Purpose: publish only a reproducible, supportable release boundary.

Inputs:

- all prior gate records
- release checklist
- release posture
- backlog

Required records:

- ReleaseGateRecord
- RedesignDecisionRecord for any unresolved architecture issue

Pass condition:

- all required gates pass
- release artifacts are reproducible
- known blockers are in canonical backlog
- support boundary is client-readable

Fail condition:

- dirty release state changes behavior without verification
- unresolved items are absent from backlog

Blocking status: `REDESIGN_REQUIRED`

Proof commands/tests:

- full release verification command from `docs/release_checklist.md`
- `git status` review for unexpected generated or stale artifacts

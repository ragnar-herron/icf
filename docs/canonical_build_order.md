STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BUILD_ORDER.md

---



## Canonical Build-Set Refactor Procedure

### Goal

Convert all scattered markup/spec files into **one coherent canonical build set** for the Truth-Seeking Interoperability Constructor Factory.

The agent must not invent new architecture. It must extract, reconcile, deduplicate, and organize the existing work into a strict build order.

---

# 1. Create a working inventory

Read every listed file and create a table:

```text
file_name
purpose
layer
status
canonical / duplicate / obsolete / evidence-only
key requirements
conflicts
```

Use these layers:

```text
L0 source inputs
L1 kernel / coalgebra truth engine
L2 catalog / STIG contract semantics
L3 live adapter family promotion
L4 live break-fix regression
L5 export projection / web_app
L6 client deliverability
L7 backlog / noncanonical notes
```

---

# 2. Classify each file

Use this mapping as the starting point.

## L0 — Source inputs

```text
assertion_contracts.json
disa_stigs.json
expert_critic_template.html
mcps/
```

## L1 — General coalgebra / constructor tests

```text
general_coalgebra_test.md
coalgebra_test.md
general_information_maturity_test.md
info_maturity_score.md
info_maturity_score_v2.md
```

## L2 — STIG domain semantics

```text
stig_coalgebra_test.md
stig_information_maturity_test.md
distinction_preserving_test.md
```

## L3 — Live adapter family promotion

```text
live_adapter_maturity_coalgebra.md
live_coverage_inventory.md
live_family_promotion_log.md
```

## L4 — Live break/fix regression

```text
LIVE_RUN_REPORT.md
get_healthy_plan.md
```

## L5 — Export / web app projection

```text
export_projection_profile_test.md
stig_expert_critic_web_app_coalgebra.md
web_app_standalone_live_f5_export_plan.md
```

## L6 — Client delivery

```text
client_deliverability_gate.md
release_checklist.md
release_posture.md
full_live_capable_stig_product_plan.md
```

## L7 — Plans / backlog / superseded patches

```text
BUILD_SPEC.md
MATURITY_BACKLOG.md
completion_plan.md
correction_plan_v1.md
```

---

# 3. Identify the canonical target documents

Collapse everything into this final build set:

```text
CANONICAL_BUILD_ORDER.md
CANONICAL_ARCHITECTURE.md
CANONICAL_GATE_SUITE.md
CANONICAL_RECORD_SCHEMAS.md
CANONICAL_DELIVERY_PROFILE.md
CANONICAL_BACKLOG.md
```

Do not keep 20+ semi-overlapping specs as active truth.

---

# 4. Build `CANONICAL_BUILD_ORDER.md`

This is the most important document.

It must say:

```text
Phase 0: Source inputs
Phase 1: Rust coalgebra kernel
Phase 2: STIG catalog / contract DSL
Phase 3: adapter family classification and promotion
Phase 4: live break/fix regression
Phase 5: export projection / web_app
Phase 6: client deliverability gate
Phase 7: release / support boundary
```

Add hard rule:

```text
No phase may start until the previous phase has emitted its required promotion artifact.
```

Required artifacts:

```text
Phase 1 -> KernelGateRecord
Phase 2 -> DistinctionCatalogRecord
Phase 3 -> LiveAdapterPromotionPortfolio
Phase 4 -> LiveRegressionEvidenceBundle
Phase 5 -> ExportProjectionGateRecord
Phase 6 -> ClientDeliverabilityGateRecord
```

---

# 5. Build `CANONICAL_ARCHITECTURE.md`

This document should contain the one whole-cloth architecture.

Required sections:

```text
1. Purpose
2. Layer model
3. Domain coalgebras
4. Maturity metric coalgebra
5. Adapter family promotion coalgebra
6. Export projection coalgebra
7. Delivery readiness coalgebra
8. Forbidden role drift
9. Status vocabulary
10. Client claim boundaries
```

Core rule to include:

```text
Factory = truth engine
Adapter = observation bridge
Export = governed projection
Client bundle = scoped deliverable
```

---

# 6. Build `CANONICAL_GATE_SUITE.md`

Merge all tests into one ordered gate suite.

Use this exact order:

```text
G0 Build-order gate
G1 General coalgebra gate
G2 STIG distinction gate
G3 Distinction-preserving maturity gate
G4 Live adapter maturity gate
G5 Live break/fix regression gate
G6 Export projection gate
G7 Client deliverability gate
G8 Release gate
```

For each gate define:

```text
purpose
inputs
required records
pass condition
fail condition
blocking status
commands/tests that prove it
```

Important: distinguish these statuses:

```text
PROJECTED_UNRESOLVED
INSUFFICIENT_EVIDENCE
BLOCKED_EXTERNAL
PROMOTED
DEMOTED
REDESIGN_REQUIRED
DELIVERABLE_SUPPORTED_ONLY
DELIVERABLE_WITH_DECLARED_BOUNDARIES
```

---

# 7. Build `CANONICAL_RECORD_SCHEMAS.md`

Collate all required records.

Minimum schemas:

```text
DistinctionCatalogRecord
MeasurableBindingRecord
LawfulPartitionRecord
AtomicPullbackRowRecord
FixtureExpectationRecord
LiveAdapterPromotionBundle
LiveAdapterPromotionPortfolio
LiveRegressionEvidenceBundle
ExternalEvidencePackage
BackupCombinedMeasurable
ExportProjectionGateRecord
ClientDeliverabilityGateRecord
MaturityGateRecord
WasteAccountingRecord
RedesignDecisionRecord
```

For each record include:

```text
purpose
producer
consumer
required fields
validation rules
example path
```

---

# 8. Build `CANONICAL_DELIVERY_PROFILE.md`

This is the client-facing truth boundary.

It must answer:

```text
What is supported live?
What is factory-validated only?
What requires external evidence?
What requires manual attestation?
What is out of scope?
What is redesign-required?
```

Include the current product claim:

```text
10 promoted live adapter families
backup blocked by external evidence
manual_or_generic eliminated by classification
client status: DELIVERABLE_SUPPORTED_ONLY or DELIVERABLE_WITH_DECLARED_BOUNDARIES
```

Do not allow “full live STIG product” unless all required live and external evidence gates pass.

---

# 9. Build `CANONICAL_BACKLOG.md`

Only unresolved work goes here.

Classify backlog items as:

```text
external_evidence_required
manual_attestation_required
adapter_family_promotion
redesign_required
release_hardening
documentation_cleanup
```

Do not mix backlog with canonical architecture.

---

# 10. Mark old files

After the canonical set is created, update the old files with one header:

```text
STATUS: SUPERSEDED BY <canonical file>
DO NOT USE AS BUILD AUTHORITY
```

For evidence files, use:

```text
STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN <canonical file>
```

For source inputs:

```text
STATUS: SOURCE INPUT
DO NOT EDIT WITHOUT RE-RUNNING CANONICAL GATES
```

---

# 11. Conflict resolution rules

When files disagree, use this priority order:

```text
1. Latest passing gate artifact
2. LiveAdapterPromotionPortfolio / ClientDeliverabilityGateRecord
3. Canonical build order
4. Source contract data
5. Older design documents
6. Patch/correction plans
```

Never resolve conflicts by prose preference.

---

# 12. Anti-muddling enforcement

Add this rule to the final canonical set:

```text
No new design document may be created unless it updates exactly one canonical document or is classified as backlog/evidence.
```

And:

```text
No software agent may claim completion unless it emits the required phase artifact and passes the corresponding canonical gate.
```

---

# 13. Final output expected from the agent

The agent must produce:

```text
/docs/canonical/CANONICAL_BUILD_ORDER.md
/docs/canonical/CANONICAL_ARCHITECTURE.md
/docs/canonical/CANONICAL_GATE_SUITE.md
/docs/canonical/CANONICAL_RECORD_SCHEMAS.md
/docs/canonical/CANONICAL_DELIVERY_PROFILE.md
/docs/canonical/CANONICAL_BACKLOG.md
/docs/canonical/SOURCE_DOCUMENT_INDEX.md
```

And a final summary:

```text
canonical_files_created
source_files_superseded
source_files_kept_as_inputs
evidence_files_kept
conflicts_resolved
open_blockers
current_client_delivery_status
```

---

# Agent instruction block

Use this verbatim:

```text
Your task is not to invent new architecture.

Your task is to refactor the existing scattered specs into a single canonical build set for the Truth-Seeking Interoperability Constructor Factory.

You must:
1. inventory every source document
2. classify it by layer
3. extract only enforceable requirements
4. remove duplicates
5. resolve conflicts by latest passing gate evidence
6. produce the canonical six-document build set
7. mark older documents as superseded, evidence-only, or source-input
8. preserve the strict build order
9. ensure no export/projection layer can be built before live adapter promotion gates
10. ensure no client-deliverable claim can exceed the passed delivery gate

Do not produce new philosophy.
Do not create another patch plan.
Do not change product behavior.
Do not write adapter code.
Do not edit UI code.

The output is a canonical build set and source-document index only.
```

Final anchor:

**One canonical build order, one canonical gate suite, one canonical record schema set, one delivery profile. Everything else becomes source, evidence, backlog, or superseded.**

# Canonical Build Order

## Status

STATUS: CANONICAL BUILD AUTHORITY

This document is the build-order authority for the Truth-Seeking Interoperability Constructor Factory. If another design note disagrees with this file, resolve the conflict by latest passing gate artifact first, then by this order.

## Inviolable Rule

No phase may start until the previous phase has emitted its required promotion artifact.

No software agent may claim completion unless it emits the required phase artifact and passes the corresponding canonical gate.

No export/projection layer may be built before live adapter promotion gates. No client-deliverable claim may exceed the passed delivery gate.

## Phase Order

| Phase | Layer | Purpose | Required Artifact | Blocking Gate |
| --- | --- | --- | --- | --- |
| Phase 0 | L0 source inputs | Collect source data, templates, and reference corpora without changing their meaning | SourceInputInventory | G0 Build-order gate |
| Phase 1 | L1 kernel / coalgebra truth engine | Build and verify the Rust coalgebra kernel and general truth-construction rules | KernelGateRecord | G1 General coalgebra gate |
| Phase 2 | L2 catalog / STIG contract semantics | Build the STIG catalog, contract DSL, lawful partitions, and distinction records | DistinctionCatalogRecord | G2 STIG distinction gate, G3 maturity gate |
| Phase 3 | L3 live adapter family promotion | Promote live adapter families by fixture, replay, and distinction-preserving evidence | LiveAdapterPromotionPortfolio | G4 Live adapter maturity gate |
| Phase 4 | L4 live break/fix regression | Run live break/fix regression and classify real findings, blocked external evidence, and unsupported controls | LiveRegressionEvidenceBundle | G5 Live break/fix regression gate |
| Phase 5 | L5 export projection / web_app | Build governed export projection and live web app surface without creating a second truth engine | ExportProjectionGateRecord | G6 Export projection gate |
| Phase 6 | L6 client deliverability | Package only supported claims and declared boundaries for client delivery | ClientDeliverabilityGateRecord | G7 Client deliverability gate |
| Phase 7 | L7 release / support boundary | Publish release posture, residual backlog, and support boundary | ReleaseGateRecord | G8 Release gate |

## Required Artifact Chain

```text
Phase 1 -> KernelGateRecord
Phase 2 -> DistinctionCatalogRecord
Phase 3 -> LiveAdapterPromotionPortfolio
Phase 4 -> LiveRegressionEvidenceBundle
Phase 5 -> ExportProjectionGateRecord
Phase 6 -> ClientDeliverabilityGateRecord
Phase 7 -> ReleaseGateRecord
```

Each artifact must cite its producer, inputs, validation command, generated timestamp, and pass/fail status.

## Conflict Priority

When files disagree, use this priority order:

1. Latest passing gate artifact
2. LiveAdapterPromotionPortfolio / ClientDeliverabilityGateRecord
3. Canonical build order
4. Source contract data
5. Older design documents
6. Patch/correction plans

Never resolve conflicts by prose preference.

## Current Build Posture

Latest bridge evidence shows 60 of 67 controls promoted and 7 controls projected unresolved. The remaining unresolved controls are classified as blocked external evidence or real open findings. This posture permits a supported-only client delivery claim, not a full live STIG product claim.

## Anti-Muddling Enforcement

No new design document may be created unless it updates exactly one canonical document or is classified as backlog/evidence.

Everything outside `docs/canonical/` is source input, evidence, backlog, or superseded guidance. It is not active build authority unless explicitly cited by a canonical document.

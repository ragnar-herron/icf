# Source Document Index

## Status

STATUS: CANONICAL SOURCE INDEX

This index classifies the scattered source documents that were collapsed into the canonical build set. JSON and executable source inputs are not edited with prose headers because that would corrupt their format; their status is recorded here.

## Inventory

| File | Purpose | Layer | Status | Canonical Interpretation | Key Requirements / Conflicts |
| --- | --- | --- | --- | --- | --- |
| `docs/assertion_contracts.json` | Machine-readable STIG assertion contracts | L0 source inputs | SOURCE INPUT | `CANONICAL_ARCHITECTURE.md`, `CANONICAL_RECORD_SCHEMAS.md` | Contract data is source input; edits require rerunning canonical gates |
| `docs/disa_stigs.json` | Raw DISA STIG corpus | L0 source inputs | SOURCE INPUT | `CANONICAL_ARCHITECTURE.md` | STIG prose source; derived contracts must trace to it |
| `docs/expert_critic_template.html` | UI template/source shell | L0 source inputs | SOURCE INPUT | `CANONICAL_GATE_SUITE.md` G6 | Template is UI source, not adjudication authority |
| `docs/mcps/` | Reference corpora and MCP notes | L0 source inputs | EVIDENCE SOURCE | `CANONICAL_ARCHITECTURE.md` | Reference/evidence only; not build authority |
| `docs/general_coalgebra_test.md` | Seven-question general coalgebra test | L1 kernel | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G1 | Do not conflate its C1-C7 with STIG C1-C20 |
| `docs/coalgebra_test.md` | Operational coalgebra test tied to scripts | L1 kernel | EVIDENCE SOURCE | `CANONICAL_GATE_SUITE.md` G1 | Demo-pass language is subordinate to latest gate records |
| `docs/general_information_maturity_test.md` | General M/E/D maturity framework | L1 kernel | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G3 | Requirements merged into maturity gates |
| `docs/info_maturity_score.md` | MaturityGateRecord schema and metrics | L1 kernel | SUPERSEDED | `CANONICAL_RECORD_SCHEMAS.md` | Schema merged into canonical record set |
| `docs/info_maturity_score_v2.md` | Stricter distinction-preserving maturity gates | L1 kernel | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G3 | Strict hard gates preserved |
| `docs/stig_coalgebra_test.md` | STIG C1-C20 checklist | L2 catalog | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G2-G3 | Checklist merged; STIG C numbering remains distinct |
| `docs/stig_information_maturity_test.md` | Executed STIG maturity review | L2 catalog | EVIDENCE SOURCE | `CANONICAL_GATE_SUITE.md` | Evidence for what ran; live counts may be stale against later bridge evidence |
| `docs/distinction_preserving_test.md` | Pullback and DP gate definitions | L2 catalog | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G3 | DP requirements preserved |
| `docs/live_adapter_maturity_coalgebra.md` | Live adapter promotion coalgebra and records | L3 adapter promotion | SUPERSEDED | `CANONICAL_ARCHITECTURE.md`, `CANONICAL_RECORD_SCHEMAS.md` | Family promotion rules preserved |
| `docs/live_coverage_inventory.md` | Supported-only scope and family mapping | L3 adapter promotion | EVIDENCE SOURCE | `CANONICAL_DELIVERY_PROFILE.md` | Contains stale absolute `icf_gpt` paths; reconcile family count by portfolio |
| `docs/live_family_promotion_log.md` | Human promotion log and holdouts | L3 adapter promotion | EVIDENCE SOURCE | `CANONICAL_BACKLOG.md` | Use for historical promotion evidence, not final claim |
| `docs/LIVE_RUN_REPORT.md` | Live campaign report | L4 live regression | EVIDENCE SOURCE | `CANONICAL_GATE_SUITE.md` G5 | Reports 6 blocked-external; latest bridge projection uses 5 blocked-external + 2 open |
| `docs/get_healthy_plan.md` | Layer 3 recovery/rebuild plan | L4 live regression | SUPERSEDED / BACKLOG | `CANONICAL_BUILD_ORDER.md`, `CANONICAL_BACKLOG.md` | Phase logic preserved; do not treat as active build authority |
| `docs/export_projection_profile_test.md` | EP projection profile gates | L5 export/web_app | SUPERSEDED | `CANONICAL_GATE_SUITE.md` G6 | EP gate laws preserved |
| `docs/stig_expert_critic_web_app_coalgebra.md` | Web app projection boundary | L5 export/web_app | SUPERSEDED | `CANONICAL_ARCHITECTURE.md`, `CANONICAL_GATE_SUITE.md` G6 | Backend-owned outcomes and no frontend judgment preserved |
| `docs/web_app_standalone_live_f5_export_plan.md` | Standalone live F5 web app plan | L5 export/web_app | BACKLOG | `CANONICAL_BACKLOG.md` | Current static wrapper vs live tool expectation is an active backlog item |
| `docs/client_deliverability_gate.md` | Supported-only client deliverability gate | L6 client delivery | SUPERSEDED | `CANONICAL_DELIVERY_PROFILE.md` | Contains stale absolute path; supported-only claim preserved |
| `docs/release_checklist.md` | Release verification checklist | L6 client delivery | EVIDENCE SOURCE | `CANONICAL_GATE_SUITE.md` G8 | Use commands as evidence; update if gate commands change |
| `docs/release_posture.md` | Release support posture | L6 client delivery | EVIDENCE SOURCE | `CANONICAL_DELIVERY_PROFILE.md` | Uses 5 blocked-external + 2 open, aligned with latest bridge projection |
| `docs/full_live_capable_stig_product_plan.md` | Roadmap to full live-capable product | L6 client delivery | BACKLOG | `CANONICAL_BACKLOG.md` | Do not use intro as current state when gate evidence says supported-only |
| `docs/BUILD_SPEC.md` | Normative ICF build specification | L7 listed, spans L1-L2 | SUPERSEDED AS ACTIVE AUTHORITY | `CANONICAL_ARCHITECTURE.md`, `CANONICAL_RECORD_SCHEMAS.md` | Core rules preserved; canonical docs are now active authority |
| `docs/MATURITY_BACKLOG.md` | Production gaps and maturity backlog | L7 backlog | EVIDENCE SOURCE / BACKLOG | `CANONICAL_BACKLOG.md` | Contains older live count evidence |
| `docs/completion_plan.md` | Remaining cleanup and verification plan | L7 backlog | BACKLOG | `CANONICAL_BACKLOG.md` | Cleanup tasks merged |
| `docs/correction_plan_v1.md` | Correction plan separating factory/live/export maturity | L7 backlog | BACKLOG | `CANONICAL_BACKLOG.md` | Three-layer capability idea preserved as backlog guidance |
| `docs/canonical_build_order.md` | Procedure that generated the canonical set | L7 procedure | EVIDENCE SOURCE | `CANONICAL_BUILD_ORDER.md` | This file is the source procedure, not build authority after canonicalization |

## Relevant Nearby Documents

| File | Classification | Note |
| --- | --- | --- |
| `docs/stig_list.csv` | SOURCE INPUT | 67-control inventory source used by coverage docs |
| `docs/robotics_coalgebra_test.md` | EVIDENCE SOURCE | Parallel domain coalgebra test, not active STIG build authority |
| `docs/robotics_information_maturity_test.md` | EVIDENCE SOURCE | Parallel domain maturity checklist |
| `coalgebra/stig_expert_critic/*` | EVIDENCE SOURCE | Runtime schemas/ledgers downstream of canonical docs |

## Conflicts Resolved

| Conflict | Resolution |
| --- | --- |
| 5 vs 6 blocked-external controls | Use latest passing bridge/export evidence for release posture: 60 promoted, 7 unresolved, classified as 5 blocked-external and 2 open findings until a newer gate run supersedes it |
| `icf_gpt` absolute paths in older docs | Treat as stale documentation; canonical docs use repo-relative paths |
| 10 vs 11 adapter families | Resolve by latest `LiveAdapterPromotionPortfolio`, not prose |
| Full live product vs supported-only delivery | Current delivery status is supported-only with declared boundaries |
| Projection-only wrapper vs live tool expectation | Active backlog item: preserve live tool while keeping projection gates |
| Dual C1 namespaces | General coalgebra C1-C7 and STIG C1-C20 are separate namespaces |

## Files Not Header-Marked

The following are classified here instead of being edited because headers would corrupt data or executable assets:

- JSON files
- CSV files
- HTML templates used as source assets
- `docs/mcps/` reference corpus
- runtime/generated artifacts

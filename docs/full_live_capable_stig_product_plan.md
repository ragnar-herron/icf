STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---

# Full Live-Capable STIG Product Plan

## Purpose

This plan defines the remaining work required to turn
`factory_exports/stig_expert_critic/web_app.py`
into a deliverable standalone STIG product that can be handed to a client.

This is not a packaging plan.

Packaging, standalone boot, local CSV runtime configuration, and live F5
connect/query are already in place.

The remaining gap is product coverage:

- most controls still do not have export-local live evaluators
- the app therefore cannot yet provide broad live STIG determination
- the product is still honest, but not yet fully deliverable as a complete
  live-capable validator

This plan is the correction path for that gap.

---

## Target Product Definition

The product is complete only when all of the following are true:

1. it is standalone at runtime
2. it loads host inventory from `stig_config_lookup/host_list.csv`
3. it loads the runtime control catalog from `stig_config_lookup/stig_list.csv`
4. it connects to and executes against a live F5
5. every control presented as live-validatable in the UI has an export-local,
   deterministic live evaluator
6. unsupported controls are not presented as live-capable
7. validation, remediation, merge, and save flows are tied to real
   export-owned code paths
8. the product can be released to a client with explicit release posture for
   any remaining non-live-supported controls

If a control is shown to the operator as live-capable, the export must own:

- evidence capture
- normalization
- comparison
- adjudication surface
- remediation guidance
- fail-safe behavior

No control may be presented as fully live-operational if any of those are
missing.

---

## Current State

What is already done:

- standalone runtime boundary
- CSV-driven runtime host list
- CSV-driven runtime control list
- local snippet/residual/session ownership
- live connect/disconnect
- live TMSH query
- live REST query
- verify -> merge -> save flow
- export-local live evaluators for:
  - `V-266084`
  - `V-266095`
  - `V-266150`
  - `V-266170`

What is not done:

- export-local live evaluators for the remaining controls
- family-by-family live coverage expansion
- product posture that separates supported controls from unsupported controls in
  the UI strongly enough
- release gates for "client deliverable" based on live coverage, not just boot
  and packaging

Observed current outcome on the live host:

- `4` supported controls evaluated live
- `63` controls returned `insufficient_evidence`

That means the standalone export is operationally incomplete as a broad STIG
validator.

---

## Non-Negotiable Rules

### R1. No parent dependency

No runtime dependency on:

- `bridge/`
- `src/`
- `rebuild_kit/`
- parent repo Python code
- parent repo Rust code
- `cargo run`

### R2. No fake live support

If a control does not have an export-local live evaluator, the UI must not make
it look like ordinary live validation is expected to work.

### R3. Family-first promotion

Controls must be implemented and promoted by evaluator family, not as scattered
one-off patches.

### R4. Evidence before optimism

A family is not considered done because a recipe exists.

A family is done only when the standalone export can:

- collect the evidence on a live F5
- normalize it deterministically
- evaluate it
- survive appliance variations expected for that family

### R5. Release posture must stay explicit

If the full catalog is not live-capable, the product release must say so.

---

## Family-Based Delivery Strategy

The remaining work should be performed by handler family from
`ControlCatalog.json`.

This matters because many controls share the same live evidence sources and the
same normalization logic.

Examples already visible in the export:

- `ltm_virtual_services`
- `ltm_virtual_ssl`
- `sshd`
- `apm_access`
- other config families visible in `handler_family`

The correct approach is:

1. pick one family
2. implement one export-local evaluator for that family
3. map all controls in that family onto that evaluator
4. live test against real appliance data
5. only then mark that family supported

This avoids endless one-control-at-a-time drift.

---

## Phased Plan

### Phase 1 - Coverage Inventory

Goal:
- produce an exact map of all controls by handler family and live-support state

Required work:
- enumerate all controls from `ControlCatalog.json`
- group by `handler_family`
- mark:
  - already supported
  - not supported
  - blocked by external evidence only
  - blocked by evaluator absence

Deliverable:
- `docs/live_coverage_inventory.md`

Exit gate:
- every control is accounted for by family and support state

### Phase 2 - Honest UI Posture

Goal:
- stop the UI from implying broad live support before coverage exists

Required work:
- add explicit filter for:
  - `Live-Supported Only`
  - `All Catalog Controls`
- relabel unsupported controls in plain language
- make `Validate All` operate on supported controls only, unless the user
  explicitly chooses full catalog mode
- show support counts in the sidebar

Deliverable:
- user-facing clarity that matches actual coverage

Exit gate:
- an operator can tell immediately which controls are truly live-capable

### Phase 3 - Family Implementation Framework

Goal:
- make family implementation systematic instead of ad hoc

Required work:
- add export-local evaluator modules or structured evaluator sections by family
- define a common evaluator interface:
  - collect
  - normalize
  - compare
  - adjudication payload
  - remediation hints
- centralize shared helpers for:
  - tmsh parsing
  - REST traversal
  - boolean/int/string normalization
  - profile/virtual attachment traversal

Deliverable:
- reusable evaluator framework inside `factory_exports/stig_expert_critic`

Exit gate:
- adding a family does not require rewriting the server each time

### Phase 4 - Implement Simple Families First

Goal:
- expand live coverage quickly with the lowest-risk families

Priority order:

1. single-scalar config families
2. simple tuple config families
3. virtual-service families
4. SSL/profile attachment families
5. APM and conditional applicability families
6. external-evidence and organization-policy families

Required work:
- implement one family at a time
- bind all controls in that family
- live test that family against the target appliance

Deliverable:
- steadily increasing live-supported control count

Exit gate:
- each implemented family has real live passes/fails on the target F5

### Phase 5 - Unsupported-Control Segmentation

Goal:
- make the product safely releasable before 100 percent coverage, if necessary

Required work:
- separate controls into:
  - `live_supported`
  - `projection_only`
  - `external_evidence_required`
  - `not_applicable_candidate`
- support release profiles:
  - `supported_only`
  - `full_catalog_with_explicit_limitations`

Deliverable:
- explicit deployment modes for client delivery

Exit gate:
- the release posture is clear and cannot be misread

### Phase 6 - Live Validation Regression Harness

Goal:
- make live coverage repeatable instead of anecdotal

Required work:
- add a repeatable harness to:
  - connect to the host from `host_list.csv`
  - run family validators
  - record outcomes
  - compare against expected shape
- keep the harness inside the export folder

Deliverable:
- repeatable live regression scripts

Exit gate:
- supported families can be rerun on demand

### Phase 7 - Remediation Flow Completion

Goal:
- ensure every supported control has an honest operational flow after detection

Required work:
- for supported families, verify:
  - recommended remediation exists
  - tmsh/rest action path is real or explicitly advisory
  - revalidate path works after remediation
  - merge/save flow is coherent where applicable

Deliverable:
- operationally complete supported families

Exit gate:
- supported controls are not detection-only dead ends

### Phase 8 - Client Deliverability Gate

Goal:
- define when the product is safe to deliver

Required work:
- add a release gate record covering:
  - standalone runtime boundary
  - live connect/query smoke
  - family support count
  - unsupported control count
  - remediation completeness for supported families
  - release posture text

Deliverable:
- `ClientDeliverabilityGateRecord`

Exit gate:
- delivery status is machine-readable and explicit

---

## Required Engineering Outputs

The following outputs should be added as the work proceeds:

- `docs/live_coverage_inventory.md`
- `docs/live_family_promotion_log.md`
- `docs/client_deliverability_gate.md`
- export-local live regression scripts
- export-local family evaluator modules or equivalent structured implementation

Optional but recommended:

- `docs/unsupported_controls_release_matrix.md`
- `docs/live_supported_controls.md`

---

## Minimum Acceptance Standard

The product may be called a full live-capable STIG product only when:

1. the runtime STIG list exposed to the client is fully backed by export-local
   live evaluators

or

2. the shipped runtime STIG list is reduced to only those controls that are
   fully export-local and live-supported

Anything else is not a full live-capable product. It is a partial live-capable
product and must be described that way.

This is the key correction.

The current app can become fully deliverable in either of two ways:

- expand live evaluator coverage to the full current catalog
- or reduce the shipped catalog to the supported subset until coverage grows

Both are valid.

Pretending the full current catalog is already live-capable is not valid.

---

## Recommended Decision Path

The fastest honest path to a client-deliverable product is:

1. implement Phase 1 and Phase 2 immediately
2. decide whether the client needs:
   - full catalog
   - or a supported-only release
3. if supported-only release is acceptable:
   - ship only supported controls first
   - continue family expansion behind it
4. if full catalog is required:
   - do not claim deliverability until the missing families are implemented

This decision should be made explicitly before further UI polish.

---

## Definition of Done

This work is done only when one of these is true:

### Full Catalog Done

- every control in `stig_list.csv` has an export-local live evaluator
- live regression passes on the target appliance
- unsupported count is zero
- release gate says deliverable

### Supported-Only Done

- `stig_list.csv` is reduced to only supported controls
- every shipped control has an export-local live evaluator
- live regression passes on the target appliance
- release gate says deliverable
- release docs explicitly state supported scope

Until then, the product is still in transition.

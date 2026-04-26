STATUS: SUPERSEDED BY docs/canonical/CANONICAL_BUILD_ORDER.md
DO NOT USE AS BUILD AUTHORITY

---

# Get Healthy Plan - Rebuild Layer 3

## Current State (verified 2026-04-23)

Layer 2 is good. The bridge pipeline produces the certified export inputs correctly.

| Metric | Value |
| ------ | ----- |
| Controls promoted (9/9 legitimacy + 10/10 DP) | 60 / 67 |
| Projected unresolved | 7 |
| Kill switch enforced | yes |
| `bridge/ExportBundle.json` | generated, 67 entries |
| `bridge/LegitimacyRecords.json` | generated, 67 records |

### The 7 unresolved controls

| Vuln ID | Title (abbrev) | Severity | Legitimacy | Live Disposition | Category |
| ------- | -------------- | -------- | ---------- | ---------------- | -------- |
| V-266074 | Local audit storage capacity | low | 6/9 | blocked-external | Needs org evidence (SSP retention policy) |
| V-266096 | Configuration backups | medium | 6/9 | blocked-external | Needs org evidence (backup schedule) |
| V-266145 | APM DoD consent banner | medium | 6/9 | blocked-external | Needs org evidence (banner text verification) |
| V-266154 | PKI revocation cache | medium | 6/9 | blocked-external | Needs org evidence (CRL/OCSP config) |
| V-266160 | Content filtering classification | medium | 6/9 | blocked-external | Needs org evidence (classification policy) |
| V-266083 | DoD certificate authority | medium | 4/9 | fail | Real finding - self-signed certificate |
| V-266174 | Always-On VPN | medium | 4/9 | fail | Real finding - VPN not configured |

These 7 are not code bugs. They are correctly projected as unresolved or open in the export surface.

---

## Build Order (strict sequential - do not skip phases)

```text
Phase 1: Delete the broken Layer 3               [git rm]
Phase 2: Build bridge/export_projection.py       [bridge/]
Phase 3: Build the HTML export                   [export/]
Phase 4: Verify EP-1 through EP-12               [bridge/]
Phase 5: Run shipping gate                       [bridge/]
Phase 6: Package the standalone web_app          [factory_exports/]
```

Each phase has an exit gate. Do not start the next phase until the current gate passes.

---

## Phase 1 - Delete the broken Layer 3

### Goal

Remove the previous broken Layer 3 implementation while preserving the data files the bridge pipeline needs.

### Steps

1. Delete all `.py` files under `factory_exports/stig_expert_critic/`.
2. Delete all `.html` files under `factory_exports/stig_expert_critic/`.
3. Delete `factory_exports/stig_expert_critic/output/`.
4. Preserve:
   - `factory_exports/stig_expert_critic/data/FactoryDistinctionBundle.json`
   - `factory_exports/stig_expert_critic/data/LiveControlOutcomeMatrix.json`
   - `factory_exports/stig_expert_critic/data/ControlCatalog.json`
   - `factory_exports/stig_expert_critic/data/ExternalEvidencePackages.json`
   - `factory_exports/stig_expert_critic/stig_config_lookup/host_list.csv`
   - `factory_exports/stig_expert_critic/stig_config_lookup/stig_list.csv`
5. Re-run `python -m bridge.promote_all`.

### Exit gate

- Zero `.py` files remain under `factory_exports/stig_expert_critic/`
- Zero `.html` files remain under `factory_exports/stig_expert_critic/`
- All six preserved data files still exist
- `python -m bridge.promote_all` still reports `60 promoted / 7 projected unresolved`

---

## Phase 2 - Build `bridge/export_projection.py`

### Goal

Create a pure projection module that reads `bridge/ExportBundle.json` and `rebuild_kit/domain_data/assertion_contracts.json`, then writes `bridge/ProjectionBundle.json`.

This module performs zero evaluation. It is a data transform only.

### Inputs

| File | Path |
| ---- | ---- |
| Export bundle | `bridge/ExportBundle.json` |
| Assertion contracts | `rebuild_kit/domain_data/assertion_contracts.json` |

### Output

`bridge/ProjectionBundle.json`

### Required output shape

Each of the 67 entries must contain:

- `vuln_id`
- `display_status`
- `stig_verdict`
- `severity`
- `title`
- `evidence_summary`
- `pullback_row`
- `legitimacy`
- `dp_gates`
- `provenance`
- `remediation`
- `explanation`
- `live_validate_enabled`

### Projection rules

1. `status == "resolved"` maps to:
   - `display_status = "live_resolved"`
   - `stig_verdict = ExportBundle.verdict`
   - `evidence_summary = pullback_row.observed`
   - `pullback_row = pass through`
   - `explanation = null`
   - `live_validate_enabled = true`

2. `status == "projected_unresolved"` with `"blocked-external"` in provenance maps to:
   - `display_status = "blocked_external"`
   - `stig_verdict = "unresolved"`
   - `evidence_summary = null`
   - `pullback_row = null`
   - `explanation = "Requires organization-provided evidence not available from the appliance. Adapter not promoted ({legitimacy})."`
   - `live_validate_enabled = false`

3. `status == "projected_unresolved"` with `"was: fail"` in provenance maps to:
   - `display_status = "open_finding"`
   - `stig_verdict = "open"`
   - `evidence_summary = null`
   - `pullback_row = null`
   - `explanation = "Real evidence fails this control. Adapter not promoted ({legitimacy})."`
   - `live_validate_enabled = false`

4. Any other `projected_unresolved` maps to:
   - `display_status = "pending_promotion"`
   - `stig_verdict = "unresolved"`
   - `evidence_summary = null`
   - `pullback_row = null`
   - `explanation = "Live evidence passes but adapter fixture suite incomplete ({legitimacy}). Awaiting promotion."`
   - `live_validate_enabled = false`

### Hard rules

- Must be importable as `from bridge.export_projection import build_projection_bundle`
- Must run as `python -m bridge.export_projection`
- Must not import `family_evaluator`, `evidence_extractor`, or `fixture_runner`
- Must not contain `eval(`, `<=`, `>=`, ` AND `, ` OR `, or `parse_criteria`

### Exit gate

`python -m bridge.export_projection` must:

- write `bridge/ProjectionBundle.json`
- report `67` entries
- report `60 live_resolved, 5 blocked_external, 2 open_finding, 0 pending_promotion`
- pass its self-test assertions

---

## Phase 3 - Build the HTML export

### Goal

Create a single self-contained HTML file at `export/stig_expert_critic.html` that renders `ProjectionBundle.json` with zero local evaluation.

### Input

`bridge/ProjectionBundle.json`

### Output

`export/stig_expert_critic.html`

### Rendering requirements

- Embed the bundle as `<script type="application/json" id="projection-data">`
- Render only from the embedded JSON
- Support filter tabs:
  - `All`
  - `Not a Finding`
  - `Open`
  - `Unresolved`
  - `Blocked`
- Support case-insensitive search by Vuln ID or title
- Render the detail panel from the selected control only
- Show `Validate Live` only when `live_validate_enabled == true`

### JS hard rules

- Zero `eval()` calls
- Zero criteria parsing
- No semantic function names: `evaluate`, `assess`, `judge`, `promote`, `witness`
- No local semantic variables: `verdict`, `pass`, `fail`
- Coverage counts come only from `display_status`

### Exit gate

`python -m bridge.build_html_export` must:

- write `export/stig_expert_critic.html`
- embed 67 controls
- report zero forbidden-token violations

---

## Phase 4 - Verify EP-1 through EP-12 gates

### Goal

Create `bridge/verify_ep_gates.py` and verify the export projection laws.

### Inputs

| File | Path |
| ---- | ---- |
| Export bundle | `bridge/ExportBundle.json` |
| Projection bundle | `bridge/ProjectionBundle.json` |
| HTML export | `export/stig_expert_critic.html` |

### Gate set

- `EP-1` No independent judgment in JS
- `EP-2` No DSL tokens in JS
- `EP-3` Unresolved preservation
- `EP-4` Promotion-only resolution
- `EP-5` Projection equivalence according to the projection law
- `EP-6` Scope count consistency
- `EP-7` Provenance preservation
- `EP-8` Validate button gating
- `EP-9` No verdict variables in JS
- `EP-10` No evaluation functions in JS
- `EP-11` Honest unresolved semantics
- `EP-12` State isolation in the detail panel

### Exit gate

`python -m bridge.verify_ep_gates` must report:

`EP GATE: PASS (12/12 gates passed)`

---

## Phase 5 - Run shipping gate evaluation

### Goal

Create `bridge/shipping_gate.py` that evaluates the export against the hard gates and maturity metrics.

### Inputs

| File | Path |
| ---- | ---- |
| Export bundle | `bridge/ExportBundle.json` |
| Projection bundle | `bridge/ProjectionBundle.json` |
| Legitimacy records | `bridge/LegitimacyRecords.json` |
| HTML export | `export/stig_expert_critic.html` |

### Hard gates

- `HG-1` ExportBundle exists and is valid
- `HG-2` Kill switch enforced
- `HG-3` All 67 controls present
- `HG-4` ProjectionBundle exists and matches
- `HG-5` HTML export exists
- `HG-6` No resolved control remains unresolved
- `HG-7` No unresolved control exposes live validate
- `HG-8` Provenance is present
- `HG-9` Promoted entries have `9/9`
- `HG-10` EP gates pass

### Aggregate thresholds

- `projection_equivalence_rate == 1.0`
- `unresolved_preservation_rate == 1.0`
- `scope_fidelity_rate == 1.0`
- `role_drift_incidents == 0`
- `frontend_truth_invention_incidents == 0`
- `waste_heat_ratio < 0.25`

### Exit gate

`python -m bridge.shipping_gate` must report:

`RESULT: SHIPPABLE`

---

## Phase 6 - Package the certified export as the standalone web_app deliverable

### Goal

Wrap the certified export artifact in a minimal standalone delivery shell at `factory_exports/stig_expert_critic/web_app.py`.

This phase does not create a new evaluator. It packages the certified projection only.

### Invariant

`factory_exports/stig_expert_critic/web_app.py` is a delivery wrapper only. It may serve files and read already-generated JSON bundles, but it may not evaluate, adjudicate, promote, parse criteria, or derive new truth.

### Inputs

| File | Path |
| ---- | ---- |
| Projection bundle | `bridge/ProjectionBundle.json` |
| Certified HTML export | `export/stig_expert_critic.html` |

### Outputs

| File | Path |
| ---- | ---- |
| Standalone HTML copy | `factory_exports/stig_expert_critic/stig_expert_critic.html` |
| Standalone projection data | `factory_exports/stig_expert_critic/data/ProjectionBundle.json` |
| Minimal delivery wrapper | `factory_exports/stig_expert_critic/web_app.py` |
| Packaging builder | `bridge/build_packaged_web_app.py` |
| Packaging verifier | `bridge/verify_packaged_export.py` |

### Delivery wrapper rules

The wrapper may:

- serve `stig_expert_critic.html`
- serve static assets if any are later added
- serve read-only JSON responses based on `ProjectionBundle.json`
- report packaging metadata

The wrapper may not:

- import `family_evaluator`, `evidence_extractor`, `fixture_runner`, or any Layer 2 evaluator
- import parent factory code outside the packaged export directory
- parse criteria or interpret DSL
- compute pass/fail/open/unresolved
- mutate projection semantics
- expose a fake live validation route

### Required implementation

#### Step 6.1 - Copy the certified artifacts into the standalone export folder

Create `bridge/build_packaged_web_app.py`.

The packaging builder must copy:

- `export/stig_expert_critic.html` -> `factory_exports/stig_expert_critic/stig_expert_critic.html`
- `bridge/ProjectionBundle.json` -> `factory_exports/stig_expert_critic/data/ProjectionBundle.json`

#### Step 6.2 - Build a minimal standalone `web_app.py`

The wrapper must:

1. run with stdlib-only Python if possible
2. serve `GET /` -> `stig_expert_critic.html`
3. serve `GET /api/projection_bundle` -> packaged `ProjectionBundle.json`
4. serve `GET /healthz` -> simple package health JSON
5. bind only to packaged files inside `factory_exports/stig_expert_critic/`
6. be generated or written by `bridge/build_packaged_web_app.py` so packaging is deterministic

#### Step 6.3 - Enforce byte-equivalence

Create `bridge/verify_packaged_export.py` that asserts:

1. packaged HTML bytes equal `export/stig_expert_critic.html`
2. packaged `ProjectionBundle.json` bytes equal `bridge/ProjectionBundle.json`
3. `web_app.py` source contains none of these forbidden tokens:
   - `family_evaluator`
   - `evidence_extractor`
   - `fixture_runner`
   - `parse_criteria`
   - `eval(`
   - `promote`
   - `witness`
   - `judge`
   - `assess`
4. `web_app.py` exposes no routes named:
   - `/api/validate`
   - `/api/validate/all`
   - `/api/remediate`
   - `/api/merge`
5. the packaged wrapper serves only packaged artifacts and read-only health/projection routes

#### Step 6.4 - Verify standalone boot

The wrapper must boot and serve the packaged projection artifact without depending on the parent factory runtime.

### Exit gate

```powershell
$env:PYTHONIOENCODING = "utf-8"
python -m bridge.build_packaged_web_app
python -m bridge.verify_packaged_export
python factory_exports/stig_expert_critic/web_app.py
```

Must satisfy:

- `build_packaged_web_app` prints `PACKAGED WEB APP WRITTEN`
- `verify_packaged_export` prints `PACKAGED EXPORT: PASS`
- `GET /` serves the packaged HTML
- `GET /api/projection_bundle` returns 67 entries
- no forbidden tokens or forbidden routes are present
- the app runs without importing parent factory evaluator code

---

## Final file inventory when all phases complete

```
bridge/
  evidence_extractor.py       (Layer 2 - exists, unchanged)
  family_evaluator.py         (Layer 2 - exists, unchanged)
  fixture_runner.py           (Layer 2 - exists, unchanged)
  export_bundler.py           (Layer 2 - exists, unchanged)
  promote_all.py              (Layer 2 - exists, unchanged)
  export_projection.py        (Phase 2 - new)
  build_html_export.py        (Phase 3 - new)
  verify_ep_gates.py          (Phase 4 - new)
  shipping_gate.py            (Phase 5 - new)
  build_packaged_web_app.py   (Phase 6 - new)
  verify_packaged_export.py   (Phase 6 - new)
  __init__.py                 (exists, unchanged)
  ExportBundle.json           (generated, unchanged)
  ProjectionBundle.json       (generated in Phase 2)
  LegitimacyRecords.json      (generated, unchanged)

export/
  stig_expert_critic.html     (Phase 3 - new, replaces the old export sprawl)

factory_exports/stig_expert_critic/
  web_app.py                  (Phase 6 - new, minimal delivery wrapper only)
  stig_expert_critic.html     (packaged copy of certified export)
  data/
    ProjectionBundle.json     (packaged copy of certified projection bundle)
```

Total new code: 6 Python modules + 1 generated HTML file + 1 minimal delivery wrapper.

---

## What the previous build got wrong (do not repeat)

| Mistake | What happened | Rule that prevents it |
| ------- | ------------- | --------------------- |
| Built export before bridge existed | A large Python/HTML surface area grew without promoted truth to render | Invariant: Layer 2 must be good before Layer 3 begins |
| Export parsed criteria DSL inline | The UI became a second evaluator | EP-1 and EP-2: export has zero semantic authority |
| Rendered projected unresolved as validation UI | Users saw actions that implied unsupported live validation | EP-8: no Validate button unless `live_validate_enabled == true` |
| No fixture testing of the export layer | Export drifted from the factory silently | EP-5: projection equivalence must remain `1.0` |
| Too many files for a projection problem | The layer became impossible to audit | Phase 2 + Phase 3 + Phase 6 limit Layer 3 to projection, rendering, and packaging only |

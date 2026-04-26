STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---

# Web App Standalone Live F5 Export Plan

## Purpose

This document corrects the target for `factory_exports/stig_expert_critic/web_app.py`.

The current packaged wrapper is not the intended product.

The intended product is:

- a standalone factory export
- deployable into arbitrary environments
- runtime-configured from local files inside `factory_exports/stig_expert_critic`
- able to connect to a live F5
- able to execute against that live F5
- free of runtime dependency on parent factory code

This plan documents the rebuild required to reach that target.

---

## Required Product Definition

`factory_exports/stig_expert_critic/web_app.py` must be:

1. standalone
2. deployable anywhere Python can run
3. free of parent factory imports and Cargo reach-back
4. runtime-configured from:
   - `factory_exports/stig_expert_critic/stig_config_lookup/host_list.csv`
   - `factory_exports/stig_expert_critic/stig_config_lookup/stig_list.csv`
5. able to connect to a live F5 using local credentials
6. able to execute read/query and governed action flows against that F5
7. restricted to dependencies present inside the export folder or Python stdlib

The app must not rely on:

- `bridge/`
- `rebuild_kit/`
- `src/`
- parent repo Python modules
- parent repo Rust code
- `cargo run`
- any file outside the standalone export package at runtime

---

## Current State

Current `factory_exports/stig_expert_critic/web_app.py`:

- serves packaged HTML
- serves packaged `ProjectionBundle.json`
- serves `/healthz`
- does not connect to live F5
- does not read `host_list.csv` as runtime host configuration
- does not read `stig_list.csv` as runtime STIG selection

That means the current wrapper is a delivery-only projection shell, not the required live export product.

This plan is therefore a correction plan, not a minor enhancement plan.

## Current Implementation Status

As of the current rebuild pass:

- Phase A: implemented
  - packaged HTML lives in `factory_exports/stig_expert_critic/stig_expert_critic.html`
  - runtime JSON stays in `factory_exports/stig_expert_critic/data/`
  - runtime CSV sources remain authoritative
- Phase B: implemented
  - `web_app.py` now reads `host_list.csv` and `stig_list.csv`
  - `GET /api/hosts` and `GET /api/stig_list` are live
  - `GET /api/contracts` is filtered by the runtime STIG list
- Phase C: implemented in code
  - standalone `f5_client.py` restored inside the export folder
  - `POST /api/login` and `POST /api/logout` are live
- Phase D: implemented in code
  - `POST /api/tmsh-query`
  - `POST /api/rest-query`
- Phase E: implemented with honest scope
  - export-local live evaluators currently implemented for:
    - `V-266084`
    - `V-266095`
    - `V-266150`
    - `V-266170`
  - unsupported controls fail safe as `insufficient_evidence`
- Phase F: implemented in code
  - snippet load/save
  - residual capture
  - verify -> merge -> save flow
  - remediation endpoints
- Phase G: partially verified
  - standalone boot and runtime-boundary verification pass locally
  - CSV-driven API verification passes locally
  - `factory_exports/stig_expert_critic/verify_live_f5_smoke.py` is now available for the live connect/query smoke
  - live F5 connect/query verification still requires valid target credentials in the deployment environment

---

## Non-Negotiable Constraints

### C1. Standalone runtime boundary

At runtime, every required input must come from within:

- `factory_exports/stig_expert_critic/`

Allowed runtime inputs:

- local HTML
- local JSON
- local CSV
- local snippets
- local residuals
- local sessions
- live F5 HTTPS responses
- operator credentials entered into the app

Forbidden runtime dependencies:

- parent factory Python modules
- parent factory Rust binaries
- parent bridge artifacts outside the export package

### C2. Runtime configuration contract

Hosts must come from:

- `stig_config_lookup/host_list.csv`

Controls shown in the UI must come from:

- `stig_config_lookup/stig_list.csv`

No hardcoded host inventory.
No hardcoded STIG list.

### C3. No semantic drift

The standalone export may not invent compliance truth that differs from the certified factory model.

If a control is not fully live-supported inside the standalone export, the app must fail safe and say so.

### C4. No fake completion

The app must not present a control as live-operational if the standalone export cannot actually execute the required evidence collection or action path for that control.

### C5. No parent-factory reach-back

No code under `factory_exports/stig_expert_critic/` may shell out to Cargo or import parent repo modules at runtime.

---

## Target Runtime Files

The standalone export folder should ultimately own its runtime surface:

- `web_app.py`
- `f5_client.py`
- `capture_runner.py`
- `stig_expert_critic.html`
- `data/*.json`
- `stig_config_lookup/host_list.csv`
- `stig_config_lookup/stig_list.csv`
- `snippets/`
- `residuals/`
- `sessions/`

Optional:

- additional local helper modules inside `factory_exports/stig_expert_critic/`

Not allowed as runtime requirements:

- `bridge/*.py`
- `bridge/*.json`
- `docs/*.html`
- any artifact copied from outside the export folder unless copied into it during packaging

---

## Rebuild Strategy

### Phase A - Restore standalone runtime inputs

Goal:
- make the export self-sufficient again as a runtime package

Required work:
- ensure packaged HTML lives in `factory_exports/stig_expert_critic/`
- ensure all required data lives in `factory_exports/stig_expert_critic/data/`
- ensure host and STIG CSVs are the authoritative runtime sources

Exit gate:
- the export folder contains all runtime data needed to boot without parent repo reads

### Phase B - Restore runtime host and control loading

Goal:
- make `web_app.py` load hosts and controls locally at runtime

Required work:
- parse `stig_config_lookup/host_list.csv`
- parse `stig_config_lookup/stig_list.csv`
- expose local endpoints such as:
  - `GET /api/hosts`
  - `GET /api/stig_list`

Exit gate:
- UI host dropdown is populated from `host_list.csv`
- sidebar control list is populated from `stig_list.csv`

### Phase C - Restore standalone live F5 connectivity

Goal:
- connect from the standalone export to a live F5 using only export-local code

Required work:
- reuse or rebuild local F5 HTTPS client support inside `factory_exports/stig_expert_critic/`
- support session creation and authenticated queries
- keep session data local to the export package

Exit gate:
- `web_app.py` can connect/disconnect against a host listed in `host_list.csv`

### Phase D - Restore governed live read/query actions

Goal:
- support live appliance reads from the standalone export

Required work:
- restore TMSH query endpoint
- restore REST query endpoint
- bind those actions to the selected host and current credentials
- keep them local to export-owned code

Exit gate:
- TMSH query works against the selected live host
- REST query works against the selected live host

### Phase E - Restore control-scoped live evaluation surface

Goal:
- provide live control evaluation only where the standalone export can genuinely support it

Required work:
- map runtime controls from `stig_list.csv`
- determine which controls can be evaluated from export-local logic/data
- fail safe for unsupported controls

Important:
- do not claim full live support unless the standalone export actually owns the path

Exit gate:
- per-control Validate behavior is honest and host-scoped
- unsupported controls remain explicitly blocked or projection-only

### Phase F - Restore merge/remediation/runtime tool flows

Goal:
- restore the operational tabs that are part of the intended live export

Required work:
- snippet load/save from local export folder
- verify/merge/save flow if still required in the standalone export
- remediation/query helpers tied to local runtime data and live F5 connection

Exit gate:
- every visible operator action in the UI is backed by standalone export code

### Phase G - Standalone compliance verification

Goal:
- prove the export is truly standalone

Required checks:
- no parent repo imports at runtime
- no `cargo run`
- no `bridge` dependency at runtime
- boot test from `factory_exports/stig_expert_critic/` alone
- live F5 connect/query smoke test
- host list sourced from CSV
- STIG list sourced from CSV

Exit gate:
- the export runs correctly from its own folder boundary

---

## Minimum Required Runtime API Surface

The standalone live export should expose, at minimum:

- `GET /`
- `GET /healthz`
- `GET /api/hosts`
- `GET /api/stig_list`
- `POST /api/connect`
- `POST /api/disconnect`
- `POST /api/tmsh_query`
- `POST /api/rest_query`

Optional, but likely required if the original UI remains:

- `POST /api/validate`
- `POST /api/validate/all`
- `POST /api/remediate/tmsh`
- `POST /api/remediate/rest`
- `POST /api/residuals/capture`
- `POST /api/verify`
- `POST /api/merge`
- `POST /api/save`
- snippet load/save endpoints

These endpoints must be backed only by export-local code and local packaged data.

---

## Verification Requirements

The standalone live export is not complete until all of the following are true:

1. boots from `factory_exports/stig_expert_critic/` without parent imports
2. reads hosts from `stig_config_lookup/host_list.csv`
3. reads controls from `stig_config_lookup/stig_list.csv`
4. connects to a live F5
5. executes at least the read/query flows against that F5
6. fails safe for unsupported control paths
7. does not shell out to Cargo
8. does not import parent factory code

---

## Immediate Next Work

The next implementation pass should do these first:

1. replace the current delivery-only `web_app.py` with a real standalone runtime shell
2. add local CSV-driven host and control endpoints
3. restore export-local live F5 session/connect/query support
4. rewire the UI so the host dropdown and STIG sidebar are runtime-driven from local CSV files

---

## Definition of Done

`factory_exports/stig_expert_critic/web_app.py` is complete only when:

- it is standalone
- it is live-capable
- it is CSV-configured at runtime
- it has no parent factory runtime dependency
- it executes correctly against a live F5 in the target environment

Until then, the current packaged wrapper should not be described as the completed standalone live export product.

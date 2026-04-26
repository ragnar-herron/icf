STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---

# Completion Plan

This file records the remaining work after the successful rebuild of the standalone export pipeline and packaged `factory_exports/stig_expert_critic/web_app` deliverable.

Current completed state:

- Phase 1 cleanup completed
- Phase 2 projection bundle build completed
- Phase 3 HTML export build completed
- Phase 4 EP gate verification completed
- Phase 5 shipping gate completed
- Phase 6 packaged standalone `web_app.py` completed
- Standalone boot smoke check completed

Current verified outcomes:

- `bridge.promote_all` reports `60 promoted / 7 projected unresolved`
- `bridge.export_projection` passes
- `bridge.build_html_export` passes
- `bridge.verify_ep_gates` passes `12/12`
- `bridge.shipping_gate` reports `SHIPPABLE`
- `bridge.build_packaged_web_app` passes
- `bridge.verify_packaged_export` passes
- packaged `web_app.py` serves `/`, `/api/projection_bundle`, and `/healthz`

## Remaining Steps

### 1. Normalize the planning docs

Goal:
- clean the remaining encoding/rendering corruption in `docs/get_healthy_plan.md`
- make the written plan match the working implementation exactly

Why this matters:
- the implementation now works, but the doc still has punctuation/rendering artifacts
- that makes future maintenance harder and risks people following stale or malformed instructions

Done when:
- `docs/get_healthy_plan.md` reads cleanly in plain UTF-8 text
- build order, Phase 6, and final inventory are visually correct

### 2. Add a single-command verification entrypoint

Goal:
- create one repeatable command that runs the full export certification flow

Minimum sequence:
- `python -m bridge.promote_all`
- `python -m bridge.export_projection`
- `python -m bridge.build_html_export`
- `python -m bridge.verify_ep_gates`
- `python -m bridge.shipping_gate`
- `python -m bridge.build_packaged_web_app`
- `python -m bridge.verify_packaged_export`

Why this matters:
- reduces operator error
- makes regressions obvious
- gives a single answer to “is the export still certified?”

Done when:
- one script or documented command runs the whole chain and exits nonzero on failure

### 3. Add CI/build enforcement

Goal:
- make drift unshippable

Enforcement targets:
- EP gates must remain `12/12`
- shipping gate must remain `SHIPPABLE`
- packaged export must remain byte-equivalent to certified export artifacts
- packaged `web_app.py` must remain delivery-only

Why this matters:
- the system is healthy now, but without enforcement it can drift back into mixed evaluator/export behavior

Done when:
- CI fails automatically if any of the above conditions break

### 4. Add an automated packaged-app smoke test

Goal:
- make the standalone wrapper boot check part of normal verification

Smoke-test requirements:
- start packaged `factory_exports/stig_expert_critic/web_app.py`
- verify `GET /` returns `200`
- verify `GET /api/projection_bundle` returns `200`
- verify `GET /healthz` returns `200`
- verify the projection bundle contains `67` entries

Why this matters:
- proves the deployable artifact works, not just the bridge files

Done when:
- boot and endpoint checks run automatically as part of verification

### 5. Decide release posture for the 7 unresolved controls

Goal:
- explicitly decide how the product is delivered with the current unresolved set

Current unresolved set:
- `5 blocked_external`
- `2 open_finding`

Decision options:
- ship exactly as-is, with honest unresolved/open statuses
- hold release pending external evidence for blocked controls
- hold release pending remediation of the two real open findings

Why this matters:
- the system is export-healthy, but release policy still needs to be explicit

Done when:
- release decision is written down and attached to the export process

### 6. Add release artifact versioning

Goal:
- give each certified export a stable, auditable package identity

Recommended artifacts to version:
- `ExportBundle.json`
- `ProjectionBundle.json`
- `export/stig_expert_critic.html`
- packaged `factory_exports/stig_expert_critic/stig_expert_critic.html`
- packaged `factory_exports/stig_expert_critic/data/ProjectionBundle.json`

Why this matters:
- makes client delivery auditable
- makes rollback and comparison straightforward

Done when:
- each export run produces a versioned or timestamped release record

### 7. Add a release checklist

Goal:
- make client delivery repeatable and fail-safe

Checklist should include:
- bridge promotion completed
- projection bundle generated
- EP gate pass confirmed
- shipping gate pass confirmed
- packaged export verified
- standalone boot verified
- unresolved-control release posture acknowledged

Done when:
- release checklist exists in docs and is used for each export

## Suggested Order

1. Normalize `docs/get_healthy_plan.md`
2. Add single-command verification
3. Add packaged-app smoke test
4. Add CI/build enforcement
5. Add release artifact versioning
6. Add release checklist
7. Decide and document release posture for unresolved controls

## Stop Conditions

Do not call this fully durable until:

- the verification chain is one-command repeatable
- CI enforces the gates
- the packaged app smoke test is automated
- release handling for the 7 unresolved controls is explicitly documented

STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_GATE_SUITE.md

---

# Release Checklist

Use this checklist for every client-facing STIG export release.

## Build and Verification

- Run `powershell -ExecutionPolicy Bypass -File scripts/verify_stig_export.ps1`
- Confirm:
  - `bridge.promote_all` passes
  - `bridge.export_projection` passes
  - `bridge.build_html_export` passes
  - `bridge.verify_ep_gates` reports `12/12`
  - `bridge.shipping_gate` reports `SHIPPABLE`
  - `bridge.build_packaged_web_app` passes
  - `bridge.verify_packaged_export` passes
  - packaged app smoke test passes

## Release Artifacts

- Run `python -m bridge.build_release_artifacts`
- Confirm the release manifest exists under `output/releases/.../release_manifest.json`
- Confirm the manifest includes:
  - `ExportBundle.json`
  - `ProjectionBundle.json`
  - `LegitimacyRecords.json`
  - `export/stig_expert_critic.html`
  - packaged `factory_exports/stig_expert_critic/stig_expert_critic.html`
  - packaged `factory_exports/stig_expert_critic/data/ProjectionBundle.json`

## Standalone Packaging

- Confirm `factory_exports/stig_expert_critic/web_app.py` is present
- Confirm `factory_exports/stig_expert_critic/stig_expert_critic.html` is present
- Confirm `factory_exports/stig_expert_critic/data/ProjectionBundle.json` is present
- Confirm `web_app.py` remains delivery-only

## Unresolved Control Posture

- Confirm the release note explicitly states:
  - `5 blocked_external`
  - `2 open_finding`
- Confirm the unresolved controls are not described as code bugs
- Confirm client delivery materials point to `docs/release_posture.md`

## Sign-off

- Verification complete
- Release artifacts versioned
- Standalone package validated
- Release posture acknowledged

STATUS: SUPERSEDED BY docs/canonical/CANONICAL_DELIVERY_PROFILE.md
DO NOT USE AS BUILD AUTHORITY

---

# Client Deliverability Gate

## Current Gate

Current deliverability posture for the standalone live export:

- release scope: `supported_only`
- selected source controls: `67`
- shipped controls: `60`
- unsupported shipped controls: `0`
- gate status: `DELIVERABLE`

This means the product is deliverable only as a supported-only release.

It is not a full-catalog live-capable release.

## Interpretation

What is deliverable now:

- a standalone export-local live F5 product
- limited to the currently supported 60-control shipped surface
- with live connect/query support
- with supported-family validate flows
- with verify -> merge -> save operator flows

What is not deliverable yet:

- the full original 67-control catalog as a live-capable product

## Required Client Release Statement

Any current client delivery should say:

- this release ships the supported live-capable subset only
- the broader source STIG catalog remains under active family-by-family promotion

## Machine-Readable Source

Current gate record:

- [ClientDeliverabilityGateRecord.json](C:\work\dev\github\icf_gpt\factory_exports\stig_expert_critic\data\ClientDeliverabilityGateRecord.json)

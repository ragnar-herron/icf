STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_DELIVERY_PROFILE.md

---

# Release Posture For Unresolved Controls

## Current posture

The export is releasable as a truthful, factory-certified product with unresolved controls left explicit in the deliverable.

This is an honest release, not a full-clear release.

## Current unresolved set

### Blocked external (5)

These controls require organization-provided evidence that cannot be derived from the appliance alone:

- `V-266074` - Local audit storage capacity
- `V-266096` - Configuration backups
- `V-266145` - APM DoD consent banner
- `V-266154` - PKI revocation cache
- `V-266160` - Content filtering classification

Release meaning:

- these controls remain unresolved by design
- they must not be represented as code defects
- they must not be represented as validated live passes

### Open findings (2)

These controls reflect real failing evidence from the current appliance state:

- `V-266083` - DoD certificate authority
- `V-266174` - Always-On VPN

Release meaning:

- these controls remain open findings in the export
- they must not be downgraded to unresolved
- they must not be hidden behind packaging or client-facing summaries

## Client delivery rule

Ship the export with the unresolved and open controls visible exactly as projected.

Do not:

- relabel blocked external controls as passed
- relabel open findings as unresolved
- claim the package is a full-clean STIG result

Do:

- describe the product as a truthful certified export
- state the unresolved/open counts in release notes
- attach the release manifest for traceability

## When to change posture

The posture changes only if one of these happens:

1. organization evidence is supplied and the blocked-external controls can be lawfully promoted
2. the two open findings are remediated and the bridge/export chain is rerun

Until then, the release posture remains:

- `60` live resolved
- `5` blocked external
- `2` open finding

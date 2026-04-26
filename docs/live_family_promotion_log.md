STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---

# Live Family Promotion Log

## Current Supported Families

Promoted into the standalone supported-only release:

- `banner`
  - `V-266070`
- `logging`
  - `V-266075`
- `manual_or_generic` (promoted subset)
  - `V-266064`
  - `V-266065`
  - `V-266066`
  - `V-266068`
  - `V-266078`
  - `V-266079`
  - `V-266080`
  - `V-266085`
  - `V-266092`
  - `V-266093`
  - `V-266094`
  - `V-266167`
- `password_policy`
  - `V-266069`
  - `V-266087`
  - `V-266088`
  - `V-266089`
  - `V-266090`
  - `V-266091`
- `ntp`
  - `V-266076`
  - `V-266077`
  - `V-266086`
- `sshd`
  - `V-266095`
- `apm_access` (promoted subset)
  - `V-266137`
  - `V-266143`
  - `V-266145`
  - `V-266146`
  - `V-266152`
  - `V-266153`
  - `V-266154`
  - `V-266155`
  - `V-266162`
  - `V-266163`
  - `V-266164`
  - `V-266165`
  - `V-266166`
  - `V-266168`
  - `V-266169`
  - `V-266171`
  - `V-266172`
  - `V-266175`
- `ltm_virtual_services`
  - `V-266084`
  - `V-266150`
- `asm_policy` (promoted subset)
  - `V-266138`
  - `V-266140`
  - `V-266141`
  - `V-266142`
  - `V-266149`
  - `V-266158`
- `afm_firewall` (promoted subset)
  - `V-266144`
  - `V-266156`
  - `V-266157`
  - `V-266159`
  - `V-266161`
- `ltm_virtual_ssl`
  - `V-266139`
  - `V-266147`
  - `V-266148`
  - `V-266170`
  - `V-266173`

## Promotion Basis

These families are now supported in the standalone export because they have:

- export-local evaluators
- live connect/query execution through `web_app.py`
- inclusion in the supported-only shipped catalog
- successful live supported regression on `132.145.154.175`

## Next Candidates

Recommended next family promotion targets:

1. `manual_or_generic` remaining controls
2. `apm_access`
3. `afm_firewall` remaining controls
4. `backup`

## Explicit Holdout

- `V-266160`
  remains outside live support because the required approved-service classification
  decision depends on ISSM/ISSO organization inputs, not appliance state alone

## Applicability Promotion

- `V-266093`
- `V-266094`

These are now promoted through an explicit `Remote - ClientCert LDAP`
applicability detector. On the current host they resolve to `not_applicable`
instead of remaining unresolved.

## Current APM Boundary

`V-266151` remains outside live support.
The current appliance/API surface in this export does not expose enough
per-request/subroutine state to claim that reauthentication-on-role-change
is being evaluated safely yet.

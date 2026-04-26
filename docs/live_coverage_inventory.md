STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_DELIVERY_PROFILE.md

---

# Live Coverage Inventory

## Current Supported-Only Release Posture

Current standalone release scope:

- `supported_only`

Runtime inventory summary:

- total controls in source `stig_list.csv`: `67`
- shipped controls in supported-only mode: `60`
- shipped controls with export-local live evaluators: `60`
- controls remaining outside the shipped supported surface: `7`

## Supported Families

Fully shipped in supported-only mode now:

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

## Families Still Outside Supported-Only Release

Not yet shipped as live-supported:

- `backup`
  - `1` control
- `afm_firewall`
  - `1` control still outside the promoted subset
- `asm_policy`
  - fully promoted into the supported-only shipped surface
- `manual_or_generic`
  - `4` controls still outside the promoted subset
- `apm_access`
  - `1` control still outside the promoted subset (`V-266151`)

## Next Simplest Expansion Targets

Recommended next family order after the current supported set:

1. `manual_or_generic`
2. `apm_access`
   only `V-266151` remains, and it still needs a defensible per-request/subroutine live path
3. `afm_firewall`
   only `V-266160` remains, and it depends on organization-approved service classification inputs
4. `backup`
   still blocked because the appliance can show UCS archives, but it cannot prove
   the required off-device storage and organization-defined scheduling frequency
   by itself

## PKI / OCSP Applicability

- `V-266093`
- `V-266094`

These two controls are now supported with an explicit applicability gate.
On the current live host they return `not_applicable` because the appliance
is configured for `tacacs`, not `Remote - ClientCert LDAP`.

## Current Live Regression

Latest supported-only live regression on `132.145.154.175`:

- shipped controls: `60`
- `50` `not_a_finding`
- `8` `open`
- `2` `not_applicable`

## Machine-Readable Source

Current machine-readable inventory:

- [LiveCoverageInventory.json](C:\work\dev\github\icf_gpt\factory_exports\stig_expert_critic\data\LiveCoverageInventory.json)

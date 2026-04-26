# Canonical Delivery Profile

## Status

STATUS: CANONICAL DELIVERY AUTHORITY

This document is the client-facing truth boundary. It states what may be claimed, what must be disclosed, and what remains outside the supported delivery.

## Delivery Claim

Current client status:

```text
DELIVERABLE_SUPPORTED_ONLY
```

The delivery may also be described as:

```text
DELIVERABLE_WITH_DECLARED_BOUNDARIES
```

Do not claim "full live STIG product" unless all required live and external evidence gates pass.

## What Is Supported Live

The current promoted bridge/export evidence supports:

- 60 of 67 controls live-resolved through promoted adapters
- promoted live adapter families represented in the promotion portfolio
- export/web_app rendering from certified projection records
- client-visible support boundaries for unresolved/open controls

The release claim must be framed as supported-only: promoted controls are live-supported; the remaining controls are not silently inferred.

## What Is Factory-Validated Only

Factory-validated-only items are records, fixtures, or source semantics that are valid within the factory but lack live adapter promotion or required external evidence.

These may be shown as evidence, backlog, or projected explanations. They may not be exposed as live-validated compliance.

## What Requires External Evidence

Controls currently requiring external evidence include:

- V-266074: local audit storage capacity / organization retention policy
- V-266096: configuration backup schedule
- V-266145: APM DoD consent banner verification
- V-266154: PKI revocation cache / CRL/OCSP policy evidence
- V-266160: content filtering classification policy

These controls must remain `BLOCKED_EXTERNAL` or equivalent unresolved status until an `ExternalEvidencePackage` passes validation.

## What Requires Manual Attestation

Manual attestation is required where organizational procedure, policy text, or human review is the admissible evidence source. Manual attestation must be packaged as an evidence record with provider, validity window, and affected controls.

Manual attestation cannot be replaced by UI text, remediation advice, or generated projection prose.

## What Is Out Of Scope

Out-of-scope items include:

- controls not in the current 67-control STIG inventory
- non-F5 BIG-IP targets unless a new source input inventory and adapter portfolio are created
- unsupported families or controls not present in the client deliverability record
- any client-side computation attempting to create a new compliance verdict

## What Is Redesign-Required

An item is redesign-required when the current record model cannot lawfully preserve the distinction needed by the source requirement. Redesign-required work must produce a `RedesignDecisionRecord`.

Examples:

- a requirement mixes appliance runtime facts with external policy facts without a combined evidence model
- a UI flow needs live execution but is currently implemented as static projection only
- a family cannot express its lawful partition through available adapter evidence

## Product Claim Constraints

Current product claim:

```text
promoted live adapter families are supported
backup and policy-dependent controls are blocked by external evidence until evidence packages pass
manual_or_generic must be eliminated by classification before live support
client status is DELIVERABLE_SUPPORTED_ONLY or DELIVERABLE_WITH_DECLARED_BOUNDARIES
```

The source procedure requested "10 promoted live adapter families." Current inventory evidence reports a different family count in some files. Resolve the exact count by latest passing `LiveAdapterPromotionPortfolio`, not by prose.

## Client Messaging

Allowed:

- "60 controls are live-supported by promoted adapters."
- "5 controls require external evidence."
- "2 controls are open findings in the current evidence."
- "Unsupported or blocked controls are declared and not represented as resolved."

Forbidden:

- "Full live STIG product" unless every required gate passes
- "All controls validated live" while any control is blocked external, open, pending, or unsupported
- "Projection-only" as a substitute for live tool functionality when the user expects live validation
- UI claims that hide support boundaries

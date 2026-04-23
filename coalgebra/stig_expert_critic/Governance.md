# Governance

P0a emits no production promotion.

For production:

- `PromotionCandidateRecord` is machine-generated.
- `PromotionRecord` requires human sign-off.
- A promotion without both authorities is invalid.
- P0a demo records are explicitly non-promotional.

Executable coverage:

- `tests/coalgebra_gate.rs::c20_governance_requires_machine_policy_and_human_signoff`
- Machine policy without human signoff is refused.
- Machine policy plus human signoff is approved.

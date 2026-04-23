# Promotion Policy

P0a does not promote the STIG expert critic.

Demo promotion evaluation is executable in `tests/coalgebra_gate.rs::c15_promotion_policy_refuses_insufficient_survivor_lineage`.

Promotion requires:

- `survived_trials >= 2` for the demo control.
- `scope_axes >= 1` for the demo fixture.
- A committed ledger batch containing witness, claim, evidence, falsifier, pullback, and batch records.
- A human promotion record for any production expert bundle.

The demo policy is intentionally insufficient for production promotion.

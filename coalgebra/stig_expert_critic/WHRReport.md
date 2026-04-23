# Optimization Guardrail

No waste-heat optimization is implemented in P0a.

Regression guardrail: any future optimization must preserve:

- falsifier yield,
- raw evidence visibility,
- failure record visibility,
- deterministic replay.

Executable coverage:

- `tests/coalgebra_gate.rs::c17_optimization_guardrail_rejects_visibility_or_falsifier_loss`
- A candidate that drops failure visibility is rejected.

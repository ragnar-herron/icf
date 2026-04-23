# Witness Test Suite

- Positive fixture: `banner_text = APPROVED` must emit `PASS_WITH_FALSIFIER`.
- Negative fixture: changing the witness expected literal to `DIFFERENT` must produce a distinguishable trace.
- Adequacy attack: a vacuous falsifier must be rejected before a pass can be emitted.
- Coarse/bad witness attack: a witness expecting `DENIED` on the seeded break evidence is rejected because it hides the seeded failure.

Executable coverage lives in `tests/p0a.rs`, `tests/coalgebra_gate.rs`, and `src/model.rs` unit tests.

# Falsifier Catalog

## F1: Observational Counterexample

- Family: `observational`
- Subject: `demo.banner.approved`
- Counterexample field: `banner_text`
- Counterexample value: `DENIED`
- Non-vacuity proof: the counterexample is a concrete observed value that would cause the `FieldEquality` pullback to fail.

## F2: Replay Mismatch

- Family: `replay`
- Subject: ledger verifier
- Trigger: the same ledger line recomputes to a different `record_hash`.
- Non-vacuity proof: `tests/p0a.rs` verifies the generated ledger and `src/ledger.rs` rejects hash mismatches.

# Reference Kernel

This directory contains the **working Rust implementation** of the ICF coalgebra kernel as of the last successful build. It is included as a reference, not as the rebuild target.

## Status

- All C1-C20 coalgebra gate items pass.
- 50+ integration tests pass (`cargo test`).
- Distinction-preserving gates DP-1 through DP-10 pass for all 67 STIG controls at the factory/fixture level.
- Ledger verification (hash chain replay) passes for demo and live ledgers.
- The kernel is deterministic: same (state, event) pair produces byte-identical observations and successor state.

## What works

- `src/model.rs` — State types, event types, observation types, and the `step` function.
- `src/ledger.rs` — Append-only JSONL ledger with SHA-256 hash chaining and offline verification.
- `src/distinction.rs` — DP-1 through DP-10 gate implementation, measurable bindings, lawful partitions, fixture evaluation.
- `src/stig_catalog.rs` — Parses `assertion_contracts.json` into a typed `DistinctionCatalog` with bindings for all 67 controls.
- `src/live.rs` — Reads live evidence manifests and produces ledger records.
- `src/campaign.rs` — Full campaign ledger from manifest + outcome matrix.
- `src/demo.rs` — Deterministic demo data generation.
- `src/report.rs` — Coalgebra gate report (C1-C20 evidence table).
- `src/maturity.rs` — Maturity gate matrix and fixture verification.
- `tests/` — 7 integration test files covering coalgebra gates, distinction gates (demo + full STIG catalog), live replay, campaign replay, maturity audits, and demo ledgers.

## What does NOT work (and why you are rebuilding)

The kernel itself is sound. The failures are in the **adapter promotion pipeline** and **export projection layer**, which are Python-based and live outside this kernel. Specifically:

1. Most adapters never progressed past `capture_only` status.
2. Fixture packs were never built for most controls.
3. The HTML export attempted to compute verdicts locally instead of projecting kernel output.
4. Per-control bespoke evaluators were written instead of generic family evaluators.

None of those problems are in this kernel. The kernel provides the truth engine; the rebuild must complete the adapter pipeline and export layer.

## How to use this reference

- Study `src/model.rs::step` to understand how the coalgebra transition works.
- Study `src/distinction.rs` to understand how DP gates evaluate measurable bindings.
- Study `src/stig_catalog.rs` to understand how `assertion_contracts.json` is parsed into typed bindings.
- Study `tests/coalgebra_gate.rs` to understand how to test the kernel.
- Study `tests/distinction_stig_catalog_gate.rs` to understand how DP gates run across all 67 controls.

## Dependencies

- `serde` 1 (with `derive`)
- `serde_json` 1.0.149
- Rust 1.78.0 (see `rust-toolchain.toml`)

No other dependencies. The kernel is intentionally minimal.

## Running (if you want to verify the reference)

```bash
cargo test
cargo run -- demo p0a
cargo run -- ledger verify ledgers/demo/p0a.jsonl
cargo run -- coalgebra report --fail-on-missing-core
```

Note: paths in the reference kernel point to the original repo layout (`coalgebra/stig_expert_critic/`, `docs/assertion_contracts.json`, etc.), not to the rebuild_kit layout. To run the reference kernel, either adjust paths or run from the original repo root.

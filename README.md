# ICF P0a Bootstrap

This repository currently implements the narrow P0a walking skeleton from
`docs/BUILD_SPEC.md`.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

That helper runs the full demo gate with fail-fast behavior:

```powershell
rustfmt --check src tests
cargo check
cargo test
cargo run -- demo p0a
cargo run -- ledger verify ledgers\demo\p0a.jsonl
cargo run -- demo break-fix
cargo run -- ledger verify ledgers\demo\break_fix.jsonl
cargo run -- coalgebra report --fail-on-missing-core
```

`icf ledger verify` is an offline check. For this P0a skeleton it requires:

- A hash-chained JSONL ledger with valid `prev_hash` and `record_hash` values.
- Only supported P0a/demo record kinds; unknown record kinds are rejected.
- Readable content-addressed evidence blobs whose SHA-256 hashes match their `EvidenceRecord`.
- At least one each of `ScopeRecord`, `WitnessRecord`, `ClaimRecord`, `EvidenceRecord`, `FalsifierRecord`, `PullbackRecord`, and a committed `BatchRecord`.
- Unique `record_id` values and unique `witness_id` values.
- `PullbackRecord` entries must appear after their supporting scope, witness, claim, evidence, and falsifier records.
- Pullback `claim_id`, `evidence_id`, `witness_id`, and `falsifier_ids` must cite prior records in the same ledger slice.
- Pullback `judgment_state` must replay from the cited `FieldEquality` witness, claim, and evidence facts.
- Any `PASS_WITH_FALSIFIER` pullback must cite a non-vacuous observational falsifier.
- `BreakFixTrialRecord` and `RemediationAdviceRecord` references must resolve and preserve advisory-only break/fix semantics.
- `PromotionDecisionRecord` and `GovernanceDecisionRecord` decisions must replay from their recorded policy inputs.
- No records may appear after the committed `BatchRecord`.

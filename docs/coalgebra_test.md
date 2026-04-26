STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_GATE_SUITE.md

---

# Coalgebra Production Test - STIG Expert Critic

This checklist is now self-reporting. The source of truth is:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

The helper expands to:

```powershell
rustfmt --check src tests
cargo check
cargo test
cargo run -- demo p0a
cargo run -- ledger verify ledgers/demo/p0a.jsonl
cargo run -- demo break-fix
cargo run -- ledger verify ledgers/demo/break_fix.jsonl
cargo run -- coalgebra report --fail-on-missing-core
```

The command `icf coalgebra report` emits the C1-C20 evidence table. Current status is `demo-pass, not production-promotable`.

## Offline Verifier Contract

For the P0a skeleton, `icf ledger verify` is intentionally narrow but non-vacuous. It recomputes the hash chain, rejects unknown record kinds, validates evidence blob SHA-256 values, requires unique IDs, requires the minimum semantic record set (`ScopeRecord`, `WitnessRecord`, `ClaimRecord`, `EvidenceRecord`, `FalsifierRecord`, `PullbackRecord`, committed `BatchRecord`), rejects records after the committed batch, requires pullbacks to appear after their supporting records, validates pullback cross-references against prior record IDs, replays `FieldEquality` judgment semantics, validates break-fix and advisory remediation references, replays promotion/governance decisions from policy inputs, and rejects `PASS_WITH_FALSIFIER` unless it cites a non-vacuous observational falsifier.

| ID | Evidence | Executable Test |
| --- | --- | --- |
| C1 | `StateSchema.json`, `StateSnapshot.json` | `c1_to_c3_have_state_observation_and_event_artifacts` |
| C2 | `ObservationSchema.json` | `c1_to_c3_have_state_observation_and_event_artifacts` |
| C3 | `EventSchema.json` | `c1_to_c3_have_state_observation_and_event_artifacts` |
| C4 | `src/model.rs::step` | `c4_step_is_deterministic` |
| C5 | `states_are_distinguishable` | `c5_distinguishes_behaviorally_different_states` |
| C6 | `FalsifierCatalog.md` | `c6_falsifier_catalog_is_non_vacuous_and_executed` |
| C7 | `ScopeRecord.json` | `c7_and_c8_scope_and_witness_presence_are_explicit` |
| C8 | `WitnessSpec.json` | `c7_and_c8_scope_and_witness_presence_are_explicit` |
| C9 | `WitnessTestSuite.md` | `c9_witness_testability_rejects_bad_witness_and_survives_good_one` |
| C10 | `BreakFixTrialRecords.jsonl`, `ledgers/demo/break_fix.jsonl` | `c10_break_fix_closure_detects_break_and_revalidates_fix` |
| C11 | `SynthesizedArtifactRecords.jsonl` | `c11_synthesized_artifact_is_rejected_after_failed_witness_attack` |
| C12 | `RawEvidenceManifest.json`, `blobstore/demo` | `c12_verifier_rejects_missing_or_tampered_evidence_blob` |
| C13 | `RemediationAdviceRecord.json` | `c13_remediation_is_advisory_and_requires_post_fix_evidence` |
| C14 | `src/ledger.rs`, demo ledgers | `c14_replay_is_deterministic_and_offline_verifiable` |
| C15 | `PromotionPolicy.md`, `PromotionRecord.json` | `c15_promotion_policy_refuses_insufficient_survivor_lineage` |
| C16 | `CriticismLedger.jsonl` | `c16_ledger_rejects_removed_or_overwritten_failure_records` |
| C17 | `WHRReport.md` | `c17_optimization_guardrail_rejects_visibility_or_falsifier_loss` |
| C18 | `run_field_equality_pullback` | `c18_direct_alignment_bypass_is_rejected` |
| C19 | `ContradictionRecords.jsonl` | `c19_contradiction_detection_records_claim_witness_evidence_mismatch` |
| C20 | `Governance.md` | `c20_governance_requires_machine_policy_and_human_signoff` |

## Pass Criteria

- Demo pass: all C1-C20 tests pass and artifacts exist.
- Production pass: all C1-C20 pass against real STIG lab evidence, signed governance records, and production key material.
- Current status: demo pass only.

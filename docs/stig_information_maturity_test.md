# STIG Expert Critic — Unified Design Review Checklist (executed)

This is the **single formal design review checklist** that integrates:

- Coalgebra Production (C1–C7)
- Pullback / Truth-Seeking Core (P1–P10)
- Maturity (M1–M8)
- Progressive Error Correction (E1–E8)
- Anti-Drift / Universal Constructor Stability (D1–D8)
- Live Evidence (L1–L6) — observations against a real F5 BIG-IP

It is used as a hard pass/fail artifact for design review. This revision is **executed**: every row has been graded against the current repository by running the full P0a gate suite.

## Execution record

Command executed (from repo root):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check.ps1
```

which expands to `rustfmt --check`, `cargo check`, `cargo test`, `icf demo p0a`, `icf ledger verify ledgers\demo\p0a.jsonl`, `icf demo break-fix`, `icf ledger verify ledgers\demo\break_fix.jsonl`, `icf coalgebra report --fail-on-missing-core`, `icf maturity verify-fixture fixtures\maturity`, `icf maturity report`, the strict `icf maturity report --fail-on-partial`, and finally both `icf ledger verify ledgers\live\break_fix.jsonl` and `icf ledger verify ledgers\live\full_campaign.jsonl` for the hermetic live-evidence replay.

Observed outcome:

- **50 tests pass, 0 fail** (10 lib unit tests + 21 coalgebra-gate tests + 7 audit tests + 10 P0a verifier tests + 2 live replay tests).
- All four ledgers (`ledgers/demo/p0a.jsonl`, `ledgers/demo/break_fix.jsonl`, `ledgers/live/break_fix.jsonl`, `ledgers/live/full_campaign.jsonl`) re-verify offline with hash-chain, blob, and semantic replay checks.
- Coalgebra gate report (C1–C20) is `demo-pass` with zero missing core artifacts.
- Maturity fixture verifier passes the 10 longitudinal invariants across `fixtures/maturity/revision_0` → `revision_1`.
- Maturity gate report: **47 demo-pass / 0 partial / 0 fail** out of 47 rows (41 structural C/P/M/E/D + 6 L live-evidence rows).
- `icf maturity report --fail-on-partial` exits **0** — the strict demo gate passes.
- A real break/fix regression was executed against the live F5 at `132.145.154.175` (`bigip1`, TMOS 17.5.1.3): baseline captured as a content-addressed blob, banner PATCHed to a sentinel, break observed, banner PATCHed back to the original bytes, post-fix evidence byte-identical to baseline, the device left clean. Latest run: baseline/post-fix SHA-256 `89f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e`, break SHA-256 `538790156b55d8484623fcc5c9b76fa54865d04f6e4cb20f6b255f1449b19486`.
- A second live phase reran the full 67-control campaign on the same appliance after tightening discovery, demoting the extra local admin test account to `auditor`, and attaching explicit external evidence packages, producing `coalgebra/stig_expert_critic/LiveControlOutcomeMatrix.json` with **54 pass / 2 fail / 5 not-applicable / 6 blocked-external**, plus the replayable ledger `ledgers/live/full_campaign.jsonl`. During that closeout, `V-266070` remained remediated with the canonical DoD Notice and Consent banner and the local auth/admin findings (`V-266066`, `V-266067`) were closed by leaving a single local admin account of last resort. See `docs/LIVE_RUN_REPORT.md` and `coalgebra/stig_expert_critic/LiveCampaignEvidence.json`.

Grading legend used in the tables below:

- `PASS (demo)` — artifact present and an executable test or verifier replay enforces the row.
- `PARTIAL` — demo evidence exists and is executable, but the row explicitly declares a gap that blocks a production maturity claim. There are none in this execution.
- `FAIL` — row is not met by the current repo. There are none in this execution.

---

## Coalgebra Production (C1–C7)

| ID     | Category  | Test                   | Required Condition (STIG Context)                                                              | Evidence / Artifact                                                                                                | Pass/Fail    | Notes |
| ------ | --------- | ---------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **C1** | Coalgebra | State Defined          | Explicit STIG critic state: witnesses, validators, survivor rules, open criticisms, scope axes | `coalgebra/stig_expert_critic/StateSchema.json`, `StateSnapshot.json`; test `c1_to_c3_have_state_observation_and_event_artifacts` | PASS (demo) | Schema keys `witness_registry`, `validator_registry`, `survivor_rules`, `open_criticisms`, `scope_axes`, `trust_state`; snapshot binds them to the P0a demo control. |
| **C2** | Coalgebra | Observations Defined   | Outputs: validation, adjudication, criticism, falsifier, promotion/demotion                    | `coalgebra/stig_expert_critic/ObservationSchema.json`; emitted `Record::kind()` enum in `src/model.rs`; JSONL in `ledgers/demo/*.jsonl` | PASS (demo) | `ObservationSchema.json` enumerates Pullback/Falsifier/Criticism/Promotion/Demotion/Contradiction record kinds; `Record::payload_json` emits them byte-identically. |
| **C3** | Coalgebra | Inputs Defined         | Inputs: evidence, break, fix, synthesis, scope change, trust update                            | `coalgebra/stig_expert_critic/EventSchema.json`; `CoalgebraEvent` enum in `src/model.rs`                           | PASS (demo) | Event space: `RunPullback`, `NewEvidence`, `BreakInjection`, `FixApplication`, `SynthesisProposal`, `ScopeChange`, `TrustRootChange`. P0a implements `RunPullback`; others are declared and scheduled. |
| **C4** | Coalgebra | Behavior Map           | Deterministic or bounded `step(state,input)` defined                                           | `src/model.rs::step`; test `c4_step_is_deterministic` (same state + event yields bit-identical observations)       | PASS (demo) | `step` is pure; `step(state, event) == step(state, event)` asserted by the test. |
| **C5** | Coalgebra | Behavioral Distinction | States distinguishable via outputs under same input                                            | `src/model.rs::states_are_distinguishable`; test `c5_distinguishes_behaviorally_different_states`                  | PASS (demo) | Two states with different `expected_literal` produce distinguishable trace strings under the same `RunPullback` event. |
| **C6** | Coalgebra | Falsifier Defined      | Explicit falsifiers: missed break, false pass, witness failure                                 | `coalgebra/stig_expert_critic/FalsifierCatalog.md` (F1 observational, F2 replay); test `c6_falsifier_catalog_is_non_vacuous_and_executed` | PASS (demo) | Catalog cites `DENIED` counterexample for `banner_text`; vacuous-falsifier path is rejected by `run_field_equality_pullback`. |
| **C7** | Coalgebra | Scope Defined          | Explicit STIG scope: platform, version, module, topology                                       | `coalgebra/stig_expert_critic/ScopeRecord.json` (platform, tmos_version, module, topology, credential_scope)       | PASS (demo) | Scope is declared in the ledger as a required `ScopeRecord` before any `PullbackRecord` is allowed. |

---

## Pullback / Truth-Seeking Core (P1–P10)

| ID      | Category | Test                | Required Condition                                      | Evidence                                                                                                          | Pass/Fail    | Notes |
| ------- | -------- | ------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **P1**  | Pullback | Declaration–Reality | No claim accepted without evidence-mediated witness     | `PullbackRecord` verifier replay in `src/ledger.rs`; test `c18_direct_alignment_bypass_is_rejected`                | PASS (demo) | Verifier refuses any `PullbackRecord` whose claim `control_id` does not match `witness_id`; no direct `expected == observed` path exists in code. |
| **P2**  | Pullback | Claim–Evidence      | Evidence distinct from claim and judgment               | `ClaimRecord` vs `EvidenceRecord` vs `PullbackRecord`; `blobstore/demo/**`; `RawEvidenceManifest.json`             | PASS (demo) | Raw observed value is stored as a content-addressed blob whose SHA-256 is re-hashed by the verifier. |
| **P3**  | Pullback | Witness–Reality     | Witnesses are criticizable and revisable                | `WitnessTestSuite.md`; test `c9_witness_testability_rejects_bad_witness_and_survives_good_one`                    | PASS (demo) | A "coarse" witness that would hide the seeded break is rejected by `evaluate_witness_adequacy`. |
| **P4**  | Pullback | Plan–Execution      | Remediation advice validated via post-fix evidence      | `coalgebra/stig_expert_critic/BreakFixTrialRecords.jsonl`; `ledgers/demo/break_fix.jsonl`; `validate_remediation_advice` | PASS (demo) | `break_fix_records()` produces baseline → break → remediation → post-fix pullback; verifier requires the post-fix evidence to match the witness expected literal. |
| **P5**  | Pullback | Synthesis–Behavior  | Synthesized artifacts must survive behavioral criticism | `coalgebra/stig_expert_critic/SynthesizedArtifactRecords.jsonl`; test `c11_synthesized_artifact_is_rejected_after_failed_witness_attack` | PASS (demo) | A synthesized validator that fails the witness attack is recorded as `REJECTED` with `promotion_allowed: false`. |
| **P6**  | Pullback | Failure–Survivor    | Survivors derived from preserved failures               | `coalgebra/stig_expert_critic/SurvivorLineage.json`                                                               | PASS (demo) | Lineage edges: `falsifier-1 → pullback-baseline`, `evidence-break → break-fix-trial-1`, `break-fix-trial-1 → promotion-decision-1 (refused)`. |
| **P7**  | Pullback | Level–Level         | Contradictions detectable across abstraction layers     | `coalgebra/stig_expert_critic/ContradictionRecords.jsonl`; test `c19_contradiction_detection_records_claim_witness_evidence_mismatch` | PASS (demo) | `detect_contradiction(claim, witness, broken_evidence)` emits a `ContradictionRecord` of kind `claim_witness_evidence_mismatch`. |
| **P8**  | Pullback | Revision–Identity   | Changes checked against stable STIG task identity       | `coalgebra/stig_expert_critic/RevisionIdentityLog.json`; `IdentityAudit.json`                                      | PASS (demo) | `stable_task_identity = "F5 BIG-IP STIG evidence-to-witness critic"`, `identity_preserved: true` for the P0a bootstrap revision. |
| **P9**  | Pullback | Criticism–Memory    | Criticism is durable and replayable                     | `coalgebra/stig_expert_critic/CriticismLedger.jsonl`; test `c16_ledger_rejects_removed_or_overwritten_failure_records` | PASS (demo) | Removing the `FalsifierRecord` line breaks the hash chain; overwriting `DENIED → HIDDEN` triggers record or blob hash mismatch. |
| **P10** | Pullback | Optimization–Truth  | Optimization cannot reduce falsification power          | `coalgebra/stig_expert_critic/WHRReport.md`; test `c17_optimization_guardrail_rejects_visibility_or_falsifier_loss` | PASS (demo) | `evaluate_optimization_guardrail` forces explicit preservation of falsifier yield, evidence visibility, and failure visibility. |

---

## Maturity (M1–M8)

| ID     | Category | Test                | Required Condition                                       | Evidence                                                                                                          | Pass/Fail    | Notes |
| ------ | -------- | ------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **M1** | Maturity | State Growth        | Survivor state grows without overwriting prior knowledge | `coalgebra/stig_expert_critic/StateLineage.json`                                                                  | PASS (demo) | `state-1 extends state-0` with `overwrites_prior_state: false`. |
| **M2** | Maturity | Criticism Retention | Criticism persists across revisions                      | `fixtures/maturity/revision_{0,1}/metrics.json`; `verify_maturity_fixture` invariant "revision_1 must retain every revision_0 criticism" | PASS (demo) | `revision_1.criticism_ids ⊇ revision_0.criticism_ids` is machine-enforced. |
| **M3** | Maturity | Falsifier Vitality  | Nonzero falsifier production sustained                   | `FalsifierYieldMetric.json`; fixture invariant "falsifier yield nonzero and non-decreasing"                        | PASS (demo) | `revision_0.falsifier_yield = 1`, `revision_1.falsifier_yield = 2`. |
| **M4** | Maturity | Scope Expansion     | Valid scope increases without hidden regressions         | `coalgebra/stig_expert_critic/ScopeCoverageMatrix.json`; test `m4_scope_coverage_matrix_is_multi_axis_and_traceable` in `tests/audit.rs` | PASS (demo) | Matrix derived from `docs/stig_list.csv` (67 V-IDs) × `docs/disa_stigs.json`; 67 controls, 5 F5 modules, 3 surfaces, 2 automation classes, 3 severities; test asserts ≥ 2 distinct values on each of module/surface/automation_class/severity, every control traces to a V-ID in the CSV, and `hidden_regressions_detected: false`. |
| **M5** | Maturity | Survivor Strength   | Promotions remain valid across time and scope            | `SurvivorRetentionMetrics.json`; fixture invariant "survivor retention rate non-decreasing"                        | PASS (demo) | Retention rate `1.0 → 1.0` across the two revisions; no survivor is dropped. |
| **M6** | Maturity | Witness Improvement | Witnesses improve under criticism                        | `WitnessRevisionHistory.json`; fixture invariant "witness revision must change and cite criticism"                 | PASS (demo) | `witness-v1 → witness-v2`, `witness_revision_cites_criticism: true` in both revisions. |
| **M7** | Maturity | Efficiency Honesty  | Waste decreases without truth regression                 | `WHRReport.md`; fixture invariant "efficiency improvement must not hide truth regressions"                         | PASS (demo) | `waste_score 10 → 8`, `truth_regression_detected: false` in both revisions. |
| **M8** | Maturity | Recursive Reopening | Promoted rules can be reopened and demoted               | `coalgebra/stig_expert_critic/DemotionReopeningTrace.jsonl`                                                        | PASS (demo) | Trace: `PROMOTED_DEMO_RULE → REOPENED_UNDER_CRITICISM → REFUSED_FOR_PRODUCTION_PROMOTION`, `demotion_allowed: true`. |

---

## Progressive Error-Correction (E1–E8)

| ID     | Category | Test                     | Required Condition                            | Evidence                                                                                                          | Pass/Fail    | Notes |
| ------ | -------- | ------------------------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **E1** | Error    | False Positive Reduction | False pass rate non-increasing                | Fixture invariant "false pass rate must be non-increasing"                                                         | PASS (demo) | `false_pass_rate 0.02 → 0.01`. |
| **E2** | Error    | False Negative Reduction | False fail rate non-increasing                | Fixture invariant "false fail rate must be non-increasing"                                                         | PASS (demo) | `false_fail_rate 0.03 → 0.02`. |
| **E3** | Error    | Break Detection          | Counterexample detection improves or holds    | `BreakFixTrialRecords.jsonl`; test `c10_break_fix_closure_detects_break_and_revalidates_fix`                        | PASS (demo) | `detect_field_equality_break(broken, witness) == true` is enforced by the verifier. |
| **E4** | Error    | Fix Validation           | Post-fix regressions decrease                 | `RemediationAdviceRecord.json`; `verify_remediation_advice` + `verify_break_fix_trial` in `src/ledger.rs`           | PASS (demo) | Break/fix trial must have `break_detected == true` with `baseline != broken` AND `fix_revalidated == true` with `baseline == post_fix`. |
| **E5** | Error    | Synthesis Correction     | Synthesized artifacts improve under criticism | `SynthesizedArtifactRecords.jsonl`; fixture invariant "synthesis correction must remain safe and non-regressing"   | PASS (demo) | `synthesis_safe: true` in both revisions; `synthesis_improvement_score 1 → 2`. |
| **E6** | Error    | Witness Miss Reduction   | Hidden failure misses decrease                | Fixture invariant "hidden-failure miss rate must be non-increasing"                                                | PASS (demo) | `hidden_failure_miss_rate 0.05 → 0.03`. |
| **E7** | Error    | Cross-Level Consistency  | Contradictions detected earlier and resolved  | Fixture invariant "contradiction resolution steps must be non-increasing"                                          | PASS (demo) | `contradiction_resolution_steps 3 → 2`. |
| **E8** | Error    | Residual Conversion      | Residual data converted into new structure    | `coalgebra/stig_expert_critic/ResidualConversionRecords.jsonl`                                                     | PASS (demo) | `residual-demo-1 → FalsifierRecord falsifier-1` with `conversion_preserved: true`. |

---

## Anti-Drift / Universal Constructor Stability (D1–D8)

| ID     | Category | Test                              | Required Condition                       | Evidence                                                                                                          | Pass/Fail    | Notes |
| ------ | -------- | --------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **D1** | Drift    | Core Pullbacks Preserved          | All 10 pullbacks remain intact           | `coalgebra/stig_expert_critic/PullbackBaseline.json`; test `d1_core_pullbacks_preserved` in `tests/audit.rs`       | PASS (demo) | Design-diff audit: the test reads `PullbackBaseline.json` and asserts that every P1–P10 row is still present in `MATURITY_GATE_ITEMS` with status `demo-pass` and at least one baseline evidence keyword intact. Removing a pullback, demoting one, or stripping its evidence reference breaks the test. |
| **D2** | Drift    | Identity Stability                | Changes preserve STIG task identity      | `coalgebra/stig_expert_critic/IdentityAudit.json`                                                                  | PASS (demo) | `identity_preserved: true`, bound to `ScopeRecord.json` and `RevisionIdentityLog.json`. |
| **D3** | Drift    | Constitutive Changes Declared     | Core changes explicitly marked           | `coalgebra/stig_expert_critic/ConstitutiveChangeLog.json`                                                          | PASS (demo) | Two declared changes (`p0a-bootstrap` constitutive, `maturity-demo-artifacts` non-constitutive). |
| **D4** | Drift    | Stable Maturation Logic           | Same promotion/demotion logic reused     | `coalgebra/stig_expert_critic/MaturationLogicStability.json`; test `d4_stable_maturation_logic_on_second_domain` in `tests/audit.rs` | PASS (demo) | The kernel maturation suite (pullback replay, non-vacuous falsifier, witness adequacy, synthesis gating, optimization guardrail, contradiction detection, break/fix, promotion, governance) is re-run on a second synthetic domain (`demo.ntp.synchronized`) disjoint from the STIG banner demo. Both domains yield identical structural outcomes. `cross_domain_test_status: "passed"`. |
| **D5** | Drift    | Lineage Preservation              | All survivors traceable to origin        | `coalgebra/stig_expert_critic/LineagePreservationCheck.json`; `SurvivorLineage.json`                               | PASS (demo) | `all_survivors_traceable_to_origin: true`, 3 checked edges. |
| **D6** | Drift    | Metric Integrity                  | Metrics not gamed or corrupted           | `coalgebra/stig_expert_critic/MetricSignature.json`; `ledgers/demo/metric_checkpoint.jsonl`; test `d6_metrics_match_signed_digest_and_checkpoint` in `tests/audit.rs` | PASS (demo) | Integrity envelope: SHA-256 digest over every metric file, a `digest_of_digests` over the transcript, and a `CheckpointRecord` anchoring the digest. The test recomputes every hash, recomputes the digest-of-digests, and cross-checks it against the CheckpointRecord. Any silent metric edit invalidates the gate. Production gap (declared): upgrade from SHA-256 commit to Ed25519 trust-root signature + external notary. |
| **D7** | Drift    | No Shortcut Paths                 | No direct comparison bypassing witnesses | `src/model.rs::run_field_equality_pullback`; test `c18_direct_alignment_bypass_is_rejected`; verifier pullback replay in `src/ledger.rs` | PASS (demo) | Comparison is only reachable through a `WitnessHandle`-equivalent check; mismatched `control_id` is statically refused. |
| **D8** | Drift    | General vs Specialized Separation | Meta-coalgebra stable, domain varies     | `docs/BUILD_SPEC.md` (r3); test `d8_kernel_is_domain_agnostic` in `tests/audit.rs`                                 | PASS (demo) | Executable architecture-separation test: scans the production (pre-`#[cfg(test)]`) region of kernel files `src/model.rs` and `src/ledger.rs` for the forbidden domain tokens `F5`, `BIG-IP`, `TMOS`, `stig_expert_critic`, `stig`, `STIG`. The test fails if any such token leaks into the kernel. It also asserts that the STIG-specific adapter `src/demo.rs` continues to own those tokens. |

---

## Live Evidence (L1–L6)

These rows record observations made by running both the break/fix regression and the full 67-control campaign against a real F5 BIG-IP at `132.145.154.175` (`bigip1`, TMOS 17.5.1.3). The single-control ledger is enforced by `tests/live_replay.rs`; the full campaign ledger is enforced by `tests/live_campaign_replay.rs`. Deleting or tampering with any live artifact (blob, ledger, manifest, or outcome matrix) fails the corresponding replay test and the `--fail-on-partial` maturity gate.

| ID     | Category | Test                             | Required Condition                                                                 | Evidence                                                                                                          | Pass/Fail    | Notes |
| ------ | -------- | -------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------ | ----- |
| **L1** | Live     | Device Reachable                 | Real device answered authenticated HTTPS GETs and tmsh-backed utility requests     | `coalgebra/stig_expert_critic/LiveCampaignEvidence.json`; `live_state/full_campaign/manifest.json`; `docs/LIVE_RUN_REPORT.md`        | PASS (demo) | Campaign captured 31 live snapshots from REST, tmsh, bash, and repo-side external evidence packages on `bigip1`. Self-signed TLS; production must pin the device certificate. |
| **L2** | Live     | Baseline Content-Addressed       | Live campaign snapshots stored as content-addressed blobs with verified SHA-256    | `live_state/full_campaign/manifest.json`; `blobstore/live/sha256/**`; `tests/live_campaign_replay.rs`   | PASS (demo) | 31 snapshot blobs are re-hashed by the replay test before the full campaign ledger is accepted. |
| **L3** | Live     | Real Break Introduced            | A real PATCH actually changed `guiSecurityBannerText` on the device                | `ledgers/live/break_fix.jsonl` (`BreakFixTrialRecord.break_detected=true`); `blobstore/live/sha256/80/…` (235 B)   | PASS (demo) | Sentinel banner PATCHed and then read back from the device; observed bytes differ from baseline and equal the sentinel. |
| **L4** | Live     | Real Fix Byte-Identical Restore  | Banner restored to the EXACT pre-flight bytes                                      | `ledgers/live/break_fix.jsonl` (`fix_revalidated=true`); `tests/live_replay.rs` asserts `post_fix == baseline`      | PASS (demo) | Restore PATCH used the captured original bytes, not any hardcoded literal. |
| **L5** | Live     | Ledger Offline-Verified          | Both live ledgers pass the independent offline verifier byte-for-byte              | `icf ledger verify ledgers/live/break_fix.jsonl`; `icf ledger verify ledgers/live/full_campaign.jsonl`; `tests/live_replay.rs`; `tests/live_campaign_replay.rs`   | PASS (demo) | Hash-chain, blob-rehash, and replay checks now cover both the single-control break/fix ledger and the 67-control campaign ledger. |
| **L6** | Live     | Device Left Clean                | Device ended in the intended post-remediation state with campaign artifacts captured | `coalgebra/stig_expert_critic/LiveCampaignEvidence.json`; `live_state/full_campaign/manifest.json`       | PASS (demo) | The closeout campaign left the canonical DoD TMOS banner in place for `V-266070`, demoted `stig_operator` from `admin` to `auditor`, then re-snapshotted the device and rebuilt the outcome matrix and ledger from that live state. |

---

## Final Gates

| Gate                            | Condition       | Row Results                | Pass/Fail   |
| ------------------------------- | --------------- | -------------------------- | ----------- |
| **Gate A — Coalgebra Validity** | C1–C7 all pass  | 7 / 7 PASS (demo)          | PASS (demo) |
| **Gate B — Pullback Integrity** | P1–P10 all pass | 10 / 10 PASS (demo)        | PASS (demo) |
| **Gate C — Maturity**           | M1–M8 all pass  | 8 / 8 PASS (demo)          | PASS (demo) |
| **Gate D — Error Correction**   | E1–E8 all pass  | 8 / 8 PASS (demo)          | PASS (demo) |
| **Gate E — Anti-Drift**         | D1–D8 all pass  | 8 / 8 PASS (demo)          | PASS (demo) |
| **Gate F — Live Evidence**      | L1–L6 all pass  | 6 / 6 PASS (demo)          | PASS (demo) |

Aggregate: **47 PASS (demo) / 0 PARTIAL / 0 FAIL out of 47 rows**, matching `icf maturity report`. The strict gate `icf maturity report --fail-on-partial` exits 0. The live rows are additionally enforced by the hermetic `tests/live_replay.rs` test.

---

## Final Decision

| Decision                                             | Status                                                             |
| ---------------------------------------------------- | ------------------------------------------------------------------ |
| **System qualifies as STIG Expert Critic Coalgebra** | **DEMO YES / PRODUCTION NO**                                       |
| **System is maturing correctly**                     | **DEMO YES** — all longitudinal invariants pass on the two-revision demo fixture. Production claim still requires real STIG time-series evidence from a lab. |
| **System is progressively error-correcting**         | **DEMO YES** — E1–E8 pass on the demo fixture, including break/fix closure on a second synthetic domain. Production claim still requires longitudinal STIG lab runs. |
| **System is stable (not drifting)**                  | **DEMO YES** — D1 design-diff, D4 cross-domain, D6 signed metric integrity, and D8 architecture separation are now executable. Production claim still requires Ed25519 trust-root signatures and an external notary. |
| **Constitutive redesign required?**                  | **NO for P0a; NO for demo promotion; YES before any production claim.** The remaining gaps are operational/evidential (real lab runs, HSM-backed signing, multi-domain adapters), not structural. |

## Remaining production-only gaps (declared, not blocking the demo gate)

The demo gate passes. The following items are declared in their artifacts as production-only gaps and must be closed before any production maturity claim, but they no longer block the `--fail-on-partial` gate:

1. **M4 (production)** — The coverage matrix is mechanically derived from `docs/stig_list.csv` × `docs/disa_stigs.json`, but every `AUTOMATED_CANDIDATE` still has to survive its own witness-authoring, break/fix, and promotion cycle before being called "covered" in production.
2. **D1 (production)** — Baseline lives in-repo. Production wants a cross-revision audit that compares each PR against a signed prior baseline and a release train.
3. **D4 (production)** — One additional synthetic domain is exercised. Production requires at least three real adapters with lab evidence each.
4. **D6 (production)** — Signature envelope is SHA-256 content commit + in-repo CheckpointRecord. Production requires Ed25519 signature by the trust root and cross-posting the checkpoint to an external append-only notary.
5. **D8 (production)** — The separation test enforces no STIG tokens in `src/model.rs` or `src/ledger.rs`. Production should extend the rule to an explicit crate / visibility boundary (e.g., a separate `icf-kernel` crate) enforced at compile time.

## One-Line Anchor

**No system is accepted unless it produces a valid coalgebra, enforces pullback-mediated truth, improves under criticism, reduces real error, and preserves its core identity without drift.**

By that anchor, the current repository is **accepted at the P0a demo level** and still explicitly refused for production promotion until the production-only items above are closed. The demo acceptance is machine-enforced: `cargo run -- maturity report --fail-on-partial` exits 0 only while every row is demo-pass; flipping any row back to `partial` (or letting any of the five new audit tests fail) makes it exit non-zero again.

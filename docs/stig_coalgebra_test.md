# Coalgebra Production Test - STIG Expert Critic

This is a formal, build-ready checklist for the Coalgebra Production Test applied to the STIG Expert Critic. It is a gate: mark Pass/Fail and capture evidence. If any row is Fail, the system does not qualify as a valid coalgebra and should not be promoted.

| ID | Test Dimension | Required Definition | Evidence / Artifact Required | Pass/Fail | Notes |
| --- | --- | --- | --- | --- | --- |
| C1 | State (`X`) | Explicit state schema for STIG critic: witness registry, validator registry, survivor rules, open criticisms, scope axes, trust state | `StateSchema.json`, example serialized state snapshot | [ ] | |
| C2 | Observation (`O`) | Explicit outputs: validation results, adjudications, criticisms, falsifiers, promotions/demotions, audit records | List of emitted record types + example JSONL traces | [ ] | |
| C3 | Event/Input (`I`) | Defined input space: new evidence, break injection, fix application, synthesis proposal, scope change, trust-root change | `EventSchema.json` + replay fixture inputs | [ ] | |
| C4 | Behavior Map (`step`) | Deterministic step function: `(state, input) -> (observations, next_state)` via pullback + validation + adjudication pipeline | `step()` implementation + deterministic replay test | [ ] | |
| C5 | Behavioral Distinction | Clear rule for distinguishing states | Bisimulation/trace comparison test suite; counterexample pair | [ ] | |
| C6 | Falsifier | Explicit falsifiers for the coalgebra claim | `FalsifierCatalog.md` + failing test cases | [ ] | |
| C7 | Scope | Declared validity axes: platform, TMOS versions, modules, topology, credential scope | `ScopeRecord.json` + coverage matrix mapping controls to scopes | [ ] | |
| C8 | Witness Presence (Pullback) | For each control, explicit witness `W` with interpretation maps from evidence and claim; no direct comparison allowed | `WitnessSpec.json` per control; proof validator uses witness | [ ] | |
| C9 | Witness Testability (Recursive Adequacy) | Witnesses are themselves criticizable | `WitnessTestSuite` + records of witness demotion/promotion | [ ] | |
| C10 | Break/Fix Closure | Closed loop exists: baseline -> break -> detect -> propose fix -> apply -> revalidate -> record criticism | `BreakFixTrialRecord` corpus | [ ] | |
| C11 | Synthesis Demotion | Synthesized validators/advice/scripts are proposals and must pass criticism before promotion | `SynthesizedArtifactRecord` lifecycle | [ ] | |
| C12 | Failure Preservation | Raw evidence and failure semantics are preserved and linked | Raw evidence blobs + linkage in ledger | [ ] | |
| C13 | Advisory-Only Remediation | Remediation outputs are advisory-only; success requires post-fix evidence | `RemediationAdviceRecord` + post-fix traces | [ ] | |
| C14 | Deterministic Replay | Frozen inputs and seeds replay to identical outputs | Replay harness + snapshot comparison reports | [ ] | |
| C15 | Promotion Gate (Survivor) | Criteria for promotion with lineage preserved | `PromotionPolicy.md` + `PromotionRecord` examples | [ ] | |
| C16 | Criticism Durability | Criticisms are append-only, never deleted, and reused | Ledger inspection + overwrite-prevention tests | [ ] | |
| C17 | Optimization Guardrail | Optimization cannot reduce falsifier yield, evidence quality, or failure visibility | `WHRReport` + regression tests | [ ] | |
| C18 | No Direct Alignment | System forbids direct `expected == observed`; comparisons go through witnesses | Static checks / code lint + failing bypass test | [ ] | |
| C19 | Multi-Level Consistency | Contradictions across claim/witness/evidence are detectable and recorded | `ContradictionRecord` examples + tests | [ ] | |
| C20 | Governance Consistency | Promotion authority is unambiguous and consistently enforced | Governance doc + signed/refused `PromotionRecord` verification | [ ] | |

## Pass Criteria

- Pass: all items C1-C20 are checked with concrete artifacts.
- Conditional Pass: C1-C7 and C8-C12 must be checked. Remaining items may be staged.
- Fail: any of C1-C7 is unchecked -> no valid coalgebra.
- Fail: C8 or C18 is unchecked -> no valid pullback system.

## Gate Rule

Run this checklist for the STIG Expert Critic. Only if Pass may the system promote it as an object-level coalgebra or allow a meta-coalgebra to operate on it.

Re-run the same checklist recursively for any new witness family, validator set, or promoted expert bundle.

## One-Line Anchor

No promotion without a passed coalgebra test; no coalgebra without explicit state, observation, inputs, step, distinction, falsifier, scope, and no validation without a witness-mediated pullback.

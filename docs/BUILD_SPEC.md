# ICF Build Specification

Version: `0.1`
Revision: `3`
Status: `normative`
Supersedes: `docs/design_doc.md`, `docs/universal_factory_design.md`, `docs/factory_build_architecture.md` (all deleted)
Changelog (r2): kernel-writer model; admission context; validator records; batch semantics; witness families; dependency-state binding; typed falsifier families; validated-criticism metrics; evaluation vs training break operators; ledger-native trust-root history; blob store with redaction; 2-of-2 promotion; contradiction records; genesis and witness-authoring sections.
Changelog (r3): two-level coalgebraic formulation (§25); new records `CoalgebraSpecRecord`, `CoalgebraAdequacyRecord`, `BehavioralEquivalenceRecord`; enforcement point E13 (no promotion of unspecified coalgebras, bound at expert-bundle granularity); `coalgebra_adequacy_fire_rate` metric; `CoalgebraSpecRecord` brought into dependency-state binding; §1.4 extended to bound the maturation coalgebra itself; OQ-10 added; OQ-5 reclassified.

## 0. TL;DR

Build a **universal recursive pullback factory**: a two-level coalgebra in which a fixed **maturation coalgebra** manufactures and trains **specialized object-level coalgebras** (expert critics) by forcing every claim, plan, artifact, and action through witness-mediated comparison against reality, preserving all failure, and promoting only what survives repeated criticism.

The STIG expert critic is the first specialized object-level coalgebra matured by this factory. It is not the whole product.

Minimal operating rules the build must enforce mechanically:

```text
No direct agreement.
No trusted witness.
No expertise without survival.
No synthesis without criticism.
No optimization without truth gain.
No closure without falsifier.
No promotion of an unspecified coalgebra.
```

## 1. Scope and non-goals

### 1.1 In scope

- A kernel that is the only legal source of alignment judgments **and** the only legal writer of the ledger.
- A training engine that forces break/fix divergence and scores survival.
- A synthesis layer that produces proposals only, never authorities.
- Domain adapters (first: F5 BIG-IP STIG).
- Expert specialization bundles containing survivor-state.
- An append-only, signed, replayable ledger with periodic external anchoring.
- A content-addressed blob store for raw evidence with adapter-declared redaction.

### 1.2 Out of scope (v0.1)

- Distributed multi-writer ledgers.
- Automated remediation of third-party systems beyond the STIG adapter's explicit, human-gated pipeline.
- Natural-language claim parsing beyond structured, adapter-provided claims.
- KMS/HSM integration beyond an interface seam; v0.1 ships a demo key-management profile only.
- GUI surfaces; v0.1 is CLI + library.

### 1.3 Non-goals

- **Replacing human reviewers.** Promotion is 2-of-2: the `survivor_model` issues `PromotionCandidateRecord`s when thresholds are met; a human promoter co-signs the resulting `PromotionRecord`. Neither party can promote alone.
- **Proving absolute correctness.** The factory produces *survivor-state under declared scope* and preserves every falsifier. It does not claim correctness outside declared scope.

### 1.4 Universality claim boundary

Universality is structural, not operational. The same record types, enforcement points, and kernel rules apply regardless of domain; all domain content lives in adapters. v0.1 does **not** assert the system can today judge `plan` vs `design` level claims. Adapters mark each abstraction level (§13) as `instantiated` or `latent`; the reconciler only operates on instantiated pairs. STIG v0.1 instantiates only `{behavior, world}`.

**The maturation coalgebra is itself bounded.** The factory (kernel + training + synthesis + promotion protocol, see §25) is the *maturation coalgebra*. Its claimed universality is structural: the same `step_maturation` applies across domains. But in v0.1 that claim has been empirically tested only in STIG scope. Each new domain requires fresh validation of the maturation coalgebra within that domain (§25.4), not merely a new adapter. OQ-10 tracks this.

## 2. Glossary (operational definitions)

Every term below has a machine meaning that maps to a record type and/or a module contract. Do not introduce any new term in the codebase without adding it here first.

| Term | Operational definition |
| --- | --- |
| **Claim** | A structured statement about a system, interpreted by an adapter into the canonical `ClaimRecord` schema. Has a level (§13) and a scope. |
| **Evidence** | Raw, attributable observation captured by an adapter. Metadata lives in the ledger as `EvidenceRecord`; raw bytes live in the blob store (§5.5), addressed by content hash. Evidence is never compared directly to a claim. |
| **Witness** | A structured, versioned, declared comparison space of a specific **witness family** (§4.1). Defined as a `WitnessRecord` carrying: family id, observable field schema, admissible interpretations (`interp`), comparison rules (`compare`), failure semantics, declared scope, version id. A witness is the *only* legal surface on which alignment may be judged. |
| **Witness family** | One of the closed enumeration of typed witness semantics defined in §4.1 (e.g., `FieldEquality`, `FieldPredicate`, `EvidencePresence`). Adding a family requires a kernel version bump. |
| **Validator** | An executable realization of a witness's comparison rules. First-class, recorded as `ValidatorRecord`, versioned by content hash, and referenced by every `PullbackRecord`. |
| **Admission context** | The snapshot of global state captured when `witness_core::admit` grants a `WitnessHandle`: witness hash, active `KeySetRecord` hash, criticism index root, revocation index root, ledger tip hash. Recorded in `PullbackRecord` as `admission_context_hash` so pullback remains deterministic w.r.t. declared inputs. |
| **Pullback** | The mediated comparison `pullback(A, B; W, ctx)` that interprets evidence `A` and claim `B` into witness `W` under admission context `ctx`, and judges alignment only inside `W`. Produces exactly one `PullbackRecord`. |
| **Falsifier** | A typed description of how a passing claim could be overturned. Partitioned into families (§4.4). Stored as `FalsifierRecord`. A pass without at least one non-vacuous falsifier is invalid (§15 E7). |
| **Criticism** | A recorded attack against any artifact (witness, validator, survivor-rule, synthesis proposal). Stored as `CriticismRecord` with lifecycle `filed → validated → retracted/overturned`. Only `validated` criticisms drive demotion and metrics. |
| **Break** | A deliberate, recorded transformation designed to produce a detectable misalignment. Partitioned into `training`, `evaluation`, and `adversarial` operators. Stored as `BreakRecord`. |
| **Fix** | A recorded transformation intended to restore alignment after a break. Stored as `FixRecord` referencing its `BreakRecord`. |
| **Survivor-state** | The accumulated evidence that a rule, witness, or validator has survived specific trials in declared scope. Represented as the time-ordered chain of `SurvivorUpdateRecord` values. |
| **Expertise** | Survivor-state at or above the promotion threshold (§12), materialized as a 2-of-2-signed `PromotionRecord`. |
| **Scope** | Declared preconditions and environment axes: domain tag, product/version tag, platform tag, configuration-family tag, plus domain-specific axes registered with `scope_core`. |
| **Environment variation axis** | A named dimension along which scope can differ (e.g., `platform`, `os_version`, `tmos_version`, `profile_family`). |
| **Contradiction** | A typed disagreement between judgments at adjacent levels or within a level across environments. Stored as `ContradictionRecord`. |
| **Adjudicator** | The single deterministic function inside `pullback_core` that turns within-witness comparison outcomes into exactly one `JudgmentState` (§3). |
| **Residual** | Evidence observed during training that no active witness claims. Stored as typed `ResidualRecord`; source material for witness proposals and criticism. |
| **Batch** | A causal group of records committed atomically via `BatchRecord { batch_id, record_hashes[], committed }`. The runtime loop emits every record inside a batch; uncommitted trailing batches are ignored on verification. |
| **Genesis** | The bootstrap event that grants initial trust (§23). Recorded as `BootstrapAttestationRecord` at the head of the chain. |
| **Object-level coalgebra** | A coalgebra whose behavior *is* the domain behavior (e.g., the STIG expert critic: evidence → judgment/criticism/survivor update). Formalized and tested against §25's C1–C7. |
| **Maturation coalgebra** | The fixed coalgebra that evaluates, criticizes, promotes, and demotes candidate object-level coalgebras. The factory itself. Must also pass §25's C1–C7. |
| **Coalgebra spec** | A first-class aggregate naming the state, observations, events, step, distinction test, falsifier, and scope of a candidate object-level coalgebra. Stored as `CoalgebraSpecRecord`. Required before a subject is admissible for promotion (E13). |
| **Behavioral equivalence** | A declared oracle-input set over which two coalgebra specs (or two validators implementing the same witness) produce identical observation streams. Recorded as `BehavioralEquivalenceRecord`. |
| **Coalgebra adequacy** | The property that a coalgebra's declared `step` and observation map are consistent with its recorded transitions. Violations are captured as `CoalgebraAdequacyRecord`. |

## 3. Judgment states

A `PullbackRecord` must carry exactly one of the following states. No other states are legal.

| State | Meaning |
| --- | --- |
| `PASS_WITH_FALSIFIER` | Alignment holds in `W` and at least one non-vacuous `FalsifierRecord` is attached. |
| `FAIL` | Alignment does not hold in `W`. Must cite the first failing comparison rule. |
| `INSUFFICIENT_EVIDENCE` | Required observable fields are absent or un-interpretable. No pass or fail may be asserted. |
| `WITNESS_REJECTED` | The selected witness failed admissibility at `witness_core::admit` time; captured in `AdmissionContext`. Reproducible from declared inputs. |
| `WITNESS_UNDER_CRITICISM` | A validated `CriticismRecord` against the witness was present in the `criticism_index_root` captured by `AdmissionContext`. Reproducible from declared inputs. |
| `PROVISIONAL` | Pass recorded against a witness whose subject state is `provisional_survivor`. See §11 for dependency-state binding rules. |

Plus two non-pullback states appearing only on survivor records:

| State | Meaning |
| --- | --- |
| `PROMOTION_CANDIDATE` | Emitted by `survivor_model` as `PromotionCandidateRecord` when §12 thresholds are met. Not a promotion. |
| `PROMOTED` / `DEMOTED` | Appear on `PromotionRecord` / `DemotionRecord`. |

CI test `tests/kernel/test_judgment_states_enum_closed.rs` asserts the enum is closed.

## 4. Kernel: invariants and module contracts

The kernel is the **minimal trust kernel** (MTK). It is the only code path that may produce alignment judgments **or** mutate the ledger.

### 4.1 `witness_core`

Owns the `WitnessRecord` schema and the closed enumeration of **witness families** below. Each family has typed `interp`, `compare`, failure semantics, and a canonical falsifier-family set.

| Family (v0.1 ships starred) | Typed core | Typical uses |
| --- | --- | --- |
| `FieldEquality`★ | observable == expected_literal_or_site_param | config equality checks (STIG banner, timeout, password policy) |
| `FieldPredicate`★ | observable satisfies closed-form predicate over typed schema | length, regex, range, set-membership |
| `EvidencePresence`★ | required evidence records exist and are internally consistent | logs present, backups recent, certificates loaded |
| `StateMachineConformance` | observed trace is accepted by declared SM | session lifecycle, auth flow (v0.2) |
| `RateOrThreshold` | rate/count over a declared window compared to a bound | connection caps, retry bounds (v0.2) |
| `BoundaryRelation` | input→output relation across a level boundary | plan↔design, design↔impl (v0.2+) |

Adding a family is a kernel version bump gated by a spec amendment. A `WitnessRecord` that does not declare every field required by its family is rejected at admit time.

Exports:
- `load_witness(id, version) -> WitnessHandle` — returns a handle only if admissibility holds in the current admission context.
- `admit(witness_hash, claim, scope, ledger_tip) -> AdmissionOutcome` — builds `AdmissionContext` (§4.7).
- Does not execute comparisons.

### 4.2 `evidence_core`

Owns the `EvidenceRecord` schema.
- Captures evidence metadata with source attribution; raw bytes go to the blob store (§5.5).
- Enforces "evidence is immutable once hashed."
- Derived or normalized evidence is a new record citing the original by hash.
- Every adapter declares a `RedactionPolicy`; redaction emits a `RedactedEvidenceRecord` that cites the original blob hash in the (access-controlled) blob store.

Exports: `ingest(source, bytes, attributes) -> EvidenceHandle`, `normalize(evidence, rule) -> EvidenceHandle`, `resolve(hash) -> EvidenceHandle`.

### 4.3 `pullback_core`

The only module that may emit `PullbackRecord`.

Signature:

```text
pullback(
  claim: &ClaimHandle,
  evidence_set: &[EvidenceHandle],
  witness: &WitnessHandle,        // carries AdmissionContext
  validator: &ValidatorHandle,    // carries ValidatorRecord hash
  batch: &BatchHandle,
) -> PullbackRecord
```

- Deterministic w.r.t. its declared inputs (§7). Pure: no wall-clock reads, no RNG, no network.
- Contains the single adjudicator that maps within-witness comparison outcomes to a `JudgmentState`.
- `PASS_WITH_FALSIFIER` emissions are rejected unless `falsifier_core::attach` has supplied ≥ 1 non-vacuous falsifier in the same batch.

### 4.4 `falsifier_core`

Owns the `FalsifierRecord` schema.

Falsifier families (closed enum):

| Family | Typed content |
| --- | --- |
| `executable` | A replayable recipe that, given specified inputs, would cause the same pullback to emit `FAIL` or `INSUFFICIENT_EVIDENCE`. |
| `observational` | A concrete evidence predicate over witness observables whose truth would overturn the pass. |
| `scope` | A concrete point in the scope lattice outside current scope where the pass would not hold. |
| `witness_adequacy` | A declared weakness in the witness (coarseness, missing observable, version drift) and the evidence class that would exploit it. |
| `environment_drift` | A declared environment axis change under which the pass should be re-evaluated. |
| `adjacent_level_contradiction` | A reference to a pullback at an adjacent level whose disagreement would overturn the pass. |
| `evidence_absence` | A declared missing evidence kind that would flip the pass to `INSUFFICIENT_EVIDENCE`; **invalid** if the judgment was `PASS_WITH_FALSIFIER` — see non-vacuity below. |

**Non-vacuity contract.** Every `FalsifierRecord` must carry a `non_vacuity_proof`:
- At least one concrete evidence instance hash, scope point, or counterexample seed where the falsifier would fire, **and**
- For a pass judgment, the falsifier cannot be satisfied merely by "required evidence absent" (the `evidence_absence` family is therefore never admissible as the sole falsifier on a pass).

Sources of falsifiers:
1. Adapter-shipped falsifier-family library, signed with the adapter's key.
2. `critic_engine` proposals, signed with the training key.
3. Human attestation, signed with a `human_attestor` role.

### 4.5 `ledger_core`

The **only** module that may mutate the ledger. Non-kernel modules submit unsigned drafts; `ledger_core` validates the declared cross-references (§6), validates scope (§4.6), validates admission context (§4.7), signs the envelope with the submitter's role key under key-set policy, and appends.

Exports:
- `submit_draft(draft: RecordDraft, batch: BatchHandle) -> DraftReceipt`
- `open_batch(reason, parent_batch?) -> BatchHandle`
- `commit_batch(batch: BatchHandle) -> BatchRecord`
- `read(path) -> Vec<ChainedRecord>`
- `verify_chain(records, trust_root_history) -> Result<()>`

Does **not** export truncate, seek-write, delete, or overwrite. Ever.

File modes:
- POSIX: `O_APPEND`.
- Windows: `FILE_APPEND_DATA` without `FILE_WRITE_DATA`.

E10 architectural test asserts that no crate outside `core/ledger_core` imports filesystem-write APIs for any path under `ledgers/`.

### 4.6 `scope_core`

Owns the scope schema, the environment-axis registry, and the sufficiency thresholds `N`, `K`.

Exports:
- `declare(scope) -> ScopeHandle` — rejects empty or unregistered scopes.
- `cover(a, b) -> Covering`
- `axes() -> Vec<AxisId>`
- `verify_axis_coverage(updates: &[SurvivorUpdateRecord], N, K) -> Result<()>` — enforces: ≥ K distinct axis names present across the updates; each such axis has ≥ 2 distinct values; Shannon entropy over values within each axis ≥ 1 bit.

### 4.7 `AdmissionContext`

```text
AdmissionContext {
  witness_record_hash,
  key_set_record_hash,       // active KeySetRecord at admit time
  criticism_index_root,      // Merkle root over validated, non-retracted criticisms
  revocation_index_root,     // Merkle root over revoked keys
  ledger_tip_hash,           // chain head at admit time
}
```

- Built by `witness_core::admit`; referenced by `PullbackRecord.admission_context_hash`.
- Re-execution under the same admission context reproduces byte-identical outputs.
- States `WITNESS_REJECTED` and `WITNESS_UNDER_CRITICISM` are derivable from this context, not from ambient global state.

### 4.8 Kernel boundary rules

- The kernel is one Rust workspace group of crates under `core/`. No non-kernel crate depends on kernel internals; access is through narrow re-exported public APIs.
- Kernel crates deny `std::time::SystemTime`, `std::net`, and `rand` via `#![forbid(...)]` and Clippy lints.
- The Python SDK exposes only *verification* of kernel outputs, never production. `tests/architectural/test_sdk_readonly.py` covers all production APIs.

## 5. Record envelope and chain integrity

### 5.1 Envelope

```text
RecordEnvelope {
  kind: string
  schema_version: u32
  signer_role: string        // "kernel", "adapter:stig", "attestor",
                             // "validator_author", "human_attestor",
                             // "human_promoter", "survivor_model",
                             // "genesis", "checkpoint_author", ...
  key_id: string
  canonical_payload: string  // JCS-canonicalized JSON
  payload_sha256: string
  signature_base64: string   // Ed25519 over canonical_payload bytes
}
```

### 5.2 Chain

```text
ChainedRecord {
  prev_hash: string | null   // null only for BootstrapAttestationRecord (§23)
  record_hash: string        // sha256(prev_hash_or_"ROOT" + "\n" + jcs(envelope))
  envelope: RecordEnvelope
}
```

### 5.3 Trust root and key-set history

Trust root is **ledger-native**. Every state transition is a `KeySetRecord`.

```text
KeySetRecord {
  key_set_id,
  parent_key_set_hash?,
  entries: [ { key_id, role, public_key_hex, added_at_batch, revoked_at_batch? } ]
}
```

- `PullbackRecord.admission_context_hash` references the active `KeySetRecord` hash at admit time.
- Replay uses historical key sets, not the current TOML file.
- `examples/demo/trust_root.toml` is a convenience mirror of the current tip `KeySetRecord`; verifiers trust the ledger, not the file.

### 5.4 Append-only enforcement and external anchoring

- Append-only file modes as in §4.5.
- **Anchoring:** `CheckpointRecord { head_hash, checkpoint_index, external_anchor_hint }` emitted every 1000 records or daily, whichever comes first. v0.1 publication mechanism = a signed git tag `ledger-head-YYYYMMDD` whose annotated message contains the checkpoint record hash. v0.2 may add a transparency log or RFC 3161 timestamp.
- Rollback/truncation is detected by verifying the latest `CheckpointRecord` matches the external anchor.

### 5.5 Blob store (raw evidence)

- The ledger records evidence **metadata** only. Raw bytes live in a separate content-addressed blob store at `blobstore/`.
- Blob store access is controlled independently of the ledger.
- Adapters declare `RedactionPolicy` per evidence kind; redacted variants are stored as new blobs and linked via `RedactedEvidenceRecord`.
- `BlobCipherPolicy` is an interface seam; v0.1 ships a pass-through implementation. KMS integration is **OQ-8**.

## 6. Data model

Every record is wrapped in §5's envelope, lives inside a `BatchRecord` (§9), and is chained by §5.2. Cross-references are by `record_hash`.

| Record | Required references | Notes |
| --- | --- | --- |
| `BootstrapAttestationRecord` | — | Only record whose `prev_hash` is `null`. Signed by ≥ 2 `genesis` keys (§23). |
| `KeySetRecord` | optional `parent_key_set_hash` | Ledger-native trust-root history (§5.3). |
| `ClaimRecord` | `scope_hash` | `{level, scope_hash, claim_body}`; level from §13. |
| `EvidenceRecord` | — | `{source, captured_at_monotonic, content_hash, attributes}`; raw bytes in blob store. |
| `RedactedEvidenceRecord` | original `EvidenceRecord` hash | Adapter-declared redaction; stored alongside original. |
| `WitnessRecord` | — | Declares `family` (§4.1) plus family-typed fields. Content-addressed `version_id`. |
| `ValidatorRecord` | `witness_version_id` | Executable realization: artifact hash, deterministic runtime spec, pinned dependencies, build provenance. |
| `ValidatorEquivalenceRecord` | ≥ 2 `ValidatorRecord` hashes + shared oracle-test set | Asserts two validators implementing the same witness are behaviorally equivalent on the oracle-test set. |
| `PullbackRecord` | 1 × `ClaimRecord`, ≥ 1 × `EvidenceRecord`, 1 × `WitnessRecord`, 1 × `ValidatorRecord`, 1 × scope, 1 × `admission_context`, `dependency_witness_states`, `batch_id` | Carries exactly one `JudgmentState`. |
| `FalsifierRecord` | 1 × `PullbackRecord` | Required for `PASS_WITH_FALSIFIER`. Typed family + non-vacuity proof. |
| `CriticismRecord` | ≥ 1 subject hash + concrete grounds (replay script, counterexample evidence hash, or invariant id with proof) | Lifecycle: `filed → validated → retracted/overturned`. |
| `CriticismValidationRecord` | 1 × `CriticismRecord` | Transitions lifecycle to `validated`; cites replay or counterexample. |
| `ContradictionRecord` | ≥ 2 `PullbackRecord` hashes + contradiction kind + severity | Kinds: `disjoint_levels`, `value_divergence`, `scope_overreach`, `temporal_order_violation`. Emitted by the reconciler. Not a judgment. |
| `BreakRecord` | 1 × target | `{operator_id, operator_partition ∈ {training, evaluation, adversarial}, seed, target}` |
| `FixRecord` | 1 × `BreakRecord` | Corrective transformation. |
| `SurvivorUpdateRecord` | 1 × subject, ≥ 1 × `PullbackRecord`, optional `BreakRecord`/`FixRecord` pair | Updates survivor score along declared axes. |
| `ResidualRecord` | 1 × `EvidenceRecord` | `{candidate_witness_hints[], attempted_explanations[], age_class, novelty_score}` (§8.1). |
| `SynthesisProposalRecord` | — | `status ∈ {proposal, retracted}` only. Kind: `plan` / `design` / `code` / `witness` / `revision` / `remediation`. |
| `SufficiencyRecord` | — | Declares domain-specific `N`, `K`, or coverage criteria overriding defaults (§12). Signed by ≥ 2 adapter-author keys + 1 `human_promoter` key. |
| `PromotionCandidateRecord` | ≥ N × `SurvivorUpdateRecord` across ≥ K axes, optional `SufficiencyRecord` | Emitted by `survivor_model` when thresholds met. |
| `PromotionRecord` | 1 × `PromotionCandidateRecord` | 2-of-2 signed: `survivor_model` + `human_promoter`. No other path to promotion. |
| `DemotionRecord` | ≥ 1 × validated `CriticismRecord` or `FalsifierRecord` fired | Immediate on trigger. |
| `WitnessRetirementRecord` | 1 × `WitnessRecord`, optional successor | Marks a witness no longer admissible for new pullbacks; historical pullbacks remain valid. |
| `CheckpointRecord` | — | Periodic head hash + external anchor hint (§5.4). |
| `BatchRecord` | `record_hashes[]`, optional `parent_batch` | `committed: bool`. Verifier ignores uncommitted trailing batches. |
| `CoalgebraSpecRecord` | ≥ 1 × `WitnessRecord`, ≥ 1 × `ValidatorRecord`, declared `level_instantiation`, scope, plus the seven C1–C7 declarations (§25.2) | First-class aggregate describing a candidate object-level coalgebra. Required by E13 for any promotion whose subject is a coalgebra (expert bundle granularity). Signed by `coalgebra_author` role. |
| `CoalgebraAdequacyRecord` | 1 × `CoalgebraSpecRecord` + concrete divergence evidence | C6 falsifier: emitted when replay detects (a) same declared state + same event producing different observations, (b) a recorded transition that the declared `step` cannot produce, or (c) an observation outside the declared `O`. Triggers immediate `DemotionRecord` of the cited coalgebra. |
| `BehavioralEquivalenceRecord` | ≥ 2 `CoalgebraSpecRecord`s **or** ≥ 2 `ValidatorRecord`s sharing a `witness_version_id`, plus a signed oracle-input set | C5 distinction test: asserts two subjects produce byte-identical observation streams over the oracle-input set. Provides the principled ground for the legacy OQ-5 witness-equivalence question. |

CI `tests/kernel/test_record_references.rs` asserts every record type declares its required references and every emitted record satisfies them.

**Subject extension.** The allowed `subject` of `PullbackRecord`, `CriticismRecord`, `FalsifierRecord`, `SurvivorUpdateRecord`, `PromotionCandidateRecord`, `PromotionRecord`, and `DemotionRecord` is extended to include `CoalgebraSpecRecord`. This lets the maturation coalgebra act on object-level coalgebras with the existing record catalog instead of a parallel set of "coalgebra-flavored" records. No new parallel record types are introduced.

## 7. Determinism and replay contract

The following functions must be **deterministic** given their declared inputs:

- `pullback_core::pullback(claim, evidence_set, witness, validator, batch)` — with `AdmissionContext` carried inside `witness`.
- `falsifier_core::attach`
- `ledger_core::record_hash`, `verify_chain`
- `witness_core::admit`
- `scope_core::cover`, `verify_axis_coverage`

Prohibited inside any of the above:

- Wall-clock reads (use monotonic counters supplied by callers).
- Random number generation (training may use RNG; seeds are stored in `BreakRecord.seed`).
- Network I/O.
- Filesystem reads other than content-addressed evidence or witness/validator resolution.

**Replay contract.** Given the ledger file, the full `KeySetRecord` history, and the blob store, an offline verifier must recompute byte-identical `payload_sha256` and `record_hash` values for every record. `tests/replay/test_byte_exact_replay.py` enforces this on the demo ledger.

## 8. Non-kernel layers

These layers are consumers of the kernel. They may propose, attack, and observe — never adjudicate or directly mutate the ledger.

### 8.1 Training engine

| Module | Responsibility |
| --- | --- |
| `critic_engine` | Orchestrates attacks; submits `CriticismRecord` drafts. |
| `breakfix_runner` | Applies break operators (partitioned into `training`/`evaluation`/`adversarial`); submits `BreakRecord`/`FixRecord` drafts. Training operators may be referenced during witness training; evaluation operators may **not** be referenced during training and are only used for promotion evidence. |
| `witness_tester` | Adversarially tests witnesses: coarseness probes, hidden-failure probes, version-drift probes. Tests are themselves specified as witnesses (recursive witness law). |
| `counterexample_miner` | Generates evidence variants scoped to unseen axis points; must produce ≥ 1 unseen-axis counterexample before a subject is promotable. |
| `survivor_model` | The only module allowed to submit `SurvivorUpdateRecord`, `PromotionCandidateRecord`, `DemotionRecord`. **Never** submits `PromotionRecord` (which requires human co-signature). |
| `residual_pool` | Typed pool of unclaimed evidence. `ResidualRecord { evidence_hash, candidate_witness_hints[], attempted_explanations[], age_class, novelty_score }`. Retention: residuals that never feed a witness proposal, criticism, or promotion within 90 days are archived (signed archival marker), not deleted. Prioritization: novelty-score descending. Deduplication: by `(adapter, evidence_schema_hash, content_hash)`. |

### 8.2 Synthesis and planning

| Module | Output kind |
| --- | --- |
| `plan_generator` | `SynthesisProposalRecord { kind = plan }` |
| `design_generator` | `SynthesisProposalRecord { kind = design }` |
| `program_synthesis` | `SynthesisProposalRecord { kind = code }` |
| `witness_proposer` | `SynthesisProposalRecord { kind = witness }` (includes a draft `WitnessRecord`) |
| `revision_proposer` | `SynthesisProposalRecord { kind = revision }` |
| `remediation_proposer` | `SynthesisProposalRecord { kind = remediation }` bound to a `PullbackRecord` with state `FAIL` |

All outputs have `status = proposal`. No synthesis module may construct `PromotionCandidateRecord` or `PromotionRecord` (E3).

### 8.3 Domain adapters

An adapter is the only way external-world facts enter the kernel. Required interfaces:

- `interpret_claim(domain_input) -> ClaimRecord`
- `collect_evidence(scope) -> Vec<EvidenceDraft>` — raw bytes go to blob store; metadata becomes `EvidenceRecord` via `ledger_core::submit_draft`.
- `normalize(evidence, rule) -> EvidenceDraft`
- `redaction_policy() -> RedactionPolicy`
- `declare_scope() -> Scope`
- `level_instantiation() -> Map<Level, {instantiated, latent}>` (§13)
- `break_operators() -> Vec<BreakOperator>` with `partition` declared
- `falsifier_library() -> Vec<FalsifierTemplate>` keyed by witness family

v0.1 ships one adapter: `adapters/stig` (F5 BIG-IP STIG), using `docs/disa_stigs.json` and `docs/stig_list.csv`.

### 8.4 Expert specializations

An expert bundle is a directory containing:

- the `WitnessRecord` and `ValidatorRecord` sets promoted for the domain,
- the `PromotionRecord` set authorizing them,
- the relevant `KeySetRecord` history,
- a replayable ledger slice proving survivor-state,
- a CLI manifest declaring the adapter and scope.

v0.1 ships `experts/stig_expert_critic` (initially empty; populated as survivor-state accumulates).

## 9. Required runtime loop

Every kernel invocation follows this order. No module may shortcut.

1. `ledger_core::open_batch(reason)` — acquires a `BatchHandle`.
2. Adapter interprets input and submits `ClaimRecord` draft.
3. Adapter collects evidence, writes blobs, submits `EvidenceRecord` draft(s) (plus `RedactedEvidenceRecord` drafts as policy requires).
4. Caller selects a witness; `witness_core::admit` builds `AdmissionContext` and returns a `WitnessHandle`.
5. Caller selects a `ValidatorRecord`; `witness_core` returns a `ValidatorHandle` bound to the witness version.
6. `pullback_core::pullback` produces exactly one `PullbackRecord` draft.
7. On `PASS_WITH_FALSIFIER`, `falsifier_core::attach` supplies ≥ 1 non-vacuous `FalsifierRecord` draft.
8. `critic_engine` runs mandatory post-judgment checks; submits `CriticismRecord` drafts as applicable.
9. `survivor_model` submits a `SurvivorUpdateRecord` draft citing the pullback and any break/fix pair.
10. `ledger_core::commit_batch` validates all drafts' cross-references, signs envelopes, appends records in causal order, and writes the final `BatchRecord { committed = true }`.

If any step fails, the batch is abandoned. Verifiers ignore uncommitted batches. `tests/kernel/test_runtime_loop_invariants.py` asserts no `PullbackRecord` in the demo ledger lives outside a committed batch.

## 10. Required training loop

For each candidate witness, validator, plan, or synthesized artifact:

1. Open a batch.
2. Identify subject and scope; establish baseline pullback against preserved evidence.
3. Inject break via `breakfix_runner` (partition declared). Record `BreakRecord`.
4. Re-run pullback; assert whether the witness exposed the break.
5. Apply fix; record `FixRecord`.
6. Re-run pullback against the fixed state; inspect unintended consequences.
7. Mine counterexamples from unseen axis points; promotion requires at least one.
8. `critic_engine` attacks the witness and validator itself; at least one `CriticismValidationRecord` per training cycle if criticisms were filed.
9. `survivor_model` writes `SurvivorUpdateRecord` citing all of the above.
10. When §12 thresholds are met, `survivor_model` writes `PromotionCandidateRecord`; a `human_promoter` review produces the 2-of-2 `PromotionRecord`.
11. Commit the batch.

## 11. Recursion termination and dependency-state binding

Artifact status lifecycle:

```text
under_criticism → provisional_survivor → promoted → (demoted → under_criticism)
```

Transitions:

- New artifacts enter at `under_criticism`.
- An artifact reaches `provisional_survivor` after surviving ≥ 2 independent break/fix trials along ≥ 2 declared axes without a detected miss.
- An artifact reaches `promoted` after satisfying §12.
- Any single fired `FalsifierRecord` or validated `CriticismRecord` causes immediate `DemotionRecord` back to `under_criticism`.

**Dependency-state binding (closes the laundering path).**

- Every `PullbackRecord` records `dependency_witness_states`: for each transitively-cited witness, validator, **and enclosing `CoalgebraSpecRecord`**, its subject state at admit time.
- Pullbacks citing only `promoted` dependencies carry their native state (`PASS_WITH_FALSIFIER`, `FAIL`, …).
- Pullbacks citing any `provisional_survivor` dependency (witness, validator, or coalgebra spec) are emitted as `PROVISIONAL` regardless of the comparison outcome; they may feed criticism and training but **may not** be cited by a `PromotionCandidateRecord`.
- Pullbacks citing any `under_criticism` dependency carry `training_only = true` in the payload; they may only feed the training engine, never survivor updates.
- Later promotion of a dependency does **not** retroactively strengthen earlier pullbacks. The strengthened verdict requires a fresh pullback; the new record `supersedes` the original. The original stays in the ledger at its original state.
- A `CoalgebraSpecRecord` that is not yet `promoted` taints every pullback under it the same way a non-promoted witness would. This prevents an unspecified or provisionally-specified coalgebra from laundering survivor-state through its contained witnesses.

## 12. Promotion and demotion policy

**Default thresholds** (in `core/scope_core/src/thresholds.rs`):

- `N = 5` `SurvivorUpdateRecord` values, each referencing a distinct `BreakRecord`/`FixRecord` pair where the witness detected the break.
- `K = 3` distinct environment-variation axes covered per §4.6 (≥ K axis names with ≥ 2 distinct values each, entropy ≥ 1 bit per axis).
- `EVAL_BREAKS_REQUIRED = 2` distinct `evaluation`-partition break operators not referenced during training, each survived.
- `UNSEEN_AXIS_COUNTEREXAMPLES = 1` counterexample from an axis point not seen during training.
- Zero open `FalsifierRecord` fires and zero open validated `CriticismRecord` against the subject at candidate time.

**Domain-specific override.** A `SufficiencyRecord` may override any threshold if it declares justification kind (`empirical_study`, `theoretical_bound`, or `domain_standard_ref`), attaches supporting evidence, and is signed by ≥ 2 adapter-author keys + 1 `human_promoter`. `PromotionRecord`s deviating from defaults must cite a `SufficiencyRecord`.

**Two-of-two promotion.** `survivor_model` emits `PromotionCandidateRecord`. A `human_promoter` reviews and co-signs the resulting `PromotionRecord`. Neither party can promote alone. Both signatures are verified by `verify_chain`.

**Coalgebra-spec precondition (E13).** When the promotion subject is an object-level coalgebra (an expert bundle or other aggregate containing kernel-step behavior), the `PromotionCandidateRecord` **must** cite a `CoalgebraSpecRecord` whose subject and scope enclose the promotion subject, and that `CoalgebraSpecRecord` must itself be in state `promoted` with no open `CoalgebraAdequacyRecord` against it. The granularity is per expert bundle, not per witness. Standalone witnesses and validators are promoted under the existing rules without a `CoalgebraSpecRecord`.

**Demotion** is immediate on any of:

- A new fired `FalsifierRecord` against the subject.
- A `CriticismRecord` transitioned to `validated` via `CriticismValidationRecord` that cites concrete divergence.
- A `KeySetRecord` that revokes a key which signed the subject.
- An upstream dependency (witness version, scope schema, validator version) changes.

Re-promotion starts from `under_criticism`; prior survivor history is preserved in the ledger but not counted.

## 13. Multi-level pullback

Minimum levels and boundaries:

```text
Goal      ─[W_goal→plan]→      Plan
Plan      ─[W_plan→design]→    Design
Design    ─[W_design→impl]→    Implementation
Impl      ─[W_impl→behav]→     Behavior
Behavior  ─[W_behav→world]→    World (reality)
```

Rules:

- Every `ClaimRecord` carries a `level ∈ {goal, plan, design, implementation, behavior, world}`.
- Boundary witnesses belong to family `BoundaryRelation` with explicit `source_level` and `destination_level`.
- Each adapter declares `level_instantiation: Level → {instantiated, latent}`. The reconciler only operates on pairs of instantiated levels.
- STIG v0.1 instantiates `{behavior, world}` only.

The **multi-level reconciler** is an incremental service driven by new record hashes. On each new `PullbackRecord` it looks for adjacent-level contradictions and, when found, submits a `ContradictionRecord` draft (with kind and severity) plus a `CriticismRecord` draft against the weaker side. It never submits `PullbackRecord`.

## 14. Metrics

### 14.1 Truth-seeking metrics (drive non-regression gates)

| Metric | Definition |
| --- | --- |
| `falsifier_yield(subject, window)` | `count(FalsifierRecord fires citing subject) / count(PullbackRecord citing subject)` in `window`. Fires are `FalsifierRecord`s that triggered `DemotionRecord` or state-flip re-pullback. |
| `validated_criticism_yield(subject, window)` | `count(CriticismRecord in status=validated citing subject) / count(PullbackRecord citing subject)`. Filed-only criticisms are excluded. |
| `counterexample_rate(witness)` | `count(BreakRecord detected by witness) / count(BreakRecord injected against witness)`. Computed separately for `training`, `evaluation`, and `adversarial` partitions. |
| `replay_fidelity(slice)` | Fraction of records whose recomputed `payload_sha256` matches the stored value. MUST be `1.0`. |
| `coalgebra_adequacy_fire_rate(spec, window)` | `count(CoalgebraAdequacyRecord citing spec) / count(PullbackRecord citing spec)` in `window`. A non-zero value demotes `spec`; regression in this metric (relative to baseline on unchanged specs) fails CI. |

Any PR must show non-regression on `falsifier_yield`, `validated_criticism_yield`, `counterexample_rate(evaluation)`, and `coalgebra_adequacy_fire_rate` (unchanged or lower) versus the last tagged baseline, and `replay_fidelity == 1.0`.

### 14.2 Cost/performance metrics (drive operational viability gates)

| Metric | Definition |
| --- | --- |
| `ledger_size_bytes(window)` | Total appended bytes in `window`. |
| `pullback_latency_p50_ms` / `p95_ms` | Wall time of `pullback_core::pullback` measured at the caller, excluding I/O. |
| `verify_throughput_records_per_sec` | Offline verifier throughput on the demo ledger. |
| `training_cost_per_promotion` | Aggregate CPU seconds of training records divided by the number of `PromotionRecord`s in `window`. |

Cost metrics drive soft gates (warnings) in v0.1 and hard gates in v0.2. CI job `metrics` runs `icf metrics diff --against <tag>`.

## 15. Enforcement points

Each invariant maps to a concrete mechanism plus a CI test. An invariant without a mechanism is not accepted.

| Id | Invariant | Mechanism | Test |
| --- | --- | --- | --- |
| **E1** | Only `pullback_core` produces alignment judgments. | `PullbackRecord::new` is `pub(crate)`; only `pullback_core` re-exports `pullback()`. | `tests/architectural/test_pullback_constructor_visibility.rs` |
| **E2** | No witness-free judgment. | `pullback()` requires a `WitnessHandle`; `WitnessHandle` is non-constructible without `witness_core::admit`. | `tests/kernel/test_no_witness_free_judgment.rs` |
| **E3** | Synthesis is never authoritative. | `SynthesisProposalRecord::status` admits `{proposal, retracted}` only. Synthesis crates cannot construct `PromotionCandidateRecord` or `PromotionRecord`. | `tests/architectural/test_synthesis_no_promotion.py` |
| **E4** | No erased failure. | `ledger_core` uses append-only file modes; exposes no truncate or seek-write. `verify_chain` rejects mutation. | `tests/kernel/test_ledger_append_only.rs`, `tests/replay/test_tamper_detection.py` |
| **E5** | No single-pass promotion. | `survivor_model::propose_promotion()` verifies §12 thresholds (including `EVAL_BREAKS_REQUIRED`, `UNSEEN_AXIS_COUNTEREXAMPLES`) and rejects otherwise. | `tests/training/test_promotion_threshold.rs` |
| **E6** | No scope collapse. | `scope_core::declare()` rejects empty or unregistered scopes; every record with a scope field is validated at append time. | `tests/kernel/test_scope_required.rs` |
| **E7** | No pass without non-vacuous falsifier. | `pullback_core::finalize()` rejects `PASS_WITH_FALSIFIER` unless ≥ 1 `FalsifierRecord` with valid `non_vacuity_proof` is present in the same batch; `evidence_absence` family is never admissible as the sole falsifier on a pass. | `tests/kernel/test_pass_requires_falsifier.rs`, `tests/kernel/test_falsifier_non_vacuity.rs` |
| **E8** | Determinism. | Kernel crates forbid `std::time::SystemTime`, `std::net`, `rand`. | `tests/kernel/test_determinism_lints.rs` (compile-fail tests) |
| **E9** | SDK is verification-only. | Python SDK files outside `sdk-py/src/icf_stig_py/attest.py` must not import private-key constructors. | `tests/architectural/test_sdk_readonly.py` |
| **E10** | Ledger mutation is kernel-only. | No crate outside `core/ledger_core` imports filesystem-write APIs for `ledgers/` paths. | `tests/architectural/test_kernel_only_ledger_writes.rs` |
| **E11** | Two-of-two promotion. | `verify_chain` rejects any `PromotionRecord` lacking both a `survivor_model` signature and a `human_promoter` signature over the same `PromotionCandidateRecord`. | `tests/kernel/test_promotion_cosignature.rs` |
| **E12** | Dependency-state binding. | `pullback_core::finalize()` computes `dependency_witness_states` from `AdmissionContext` and emits `PROVISIONAL` / `training_only=true` as required. `survivor_model` rejects `PromotionCandidateRecord` citing any `PROVISIONAL` or `training_only` pullback. | `tests/kernel/test_dependency_state_binding.rs`, `tests/training/test_no_provisional_promotion.rs` |
| **E13** | No promotion of an unspecified object-level coalgebra. | `survivor_model::propose_promotion()` inspects the subject: if it is an expert bundle (or other aggregate flagged `coalgebra_subject = true` in the adapter manifest), it refuses to emit a `PromotionCandidateRecord` unless an enclosing `CoalgebraSpecRecord` is in state `promoted` with no open `CoalgebraAdequacyRecord`. `verify_chain` re-checks this at append. Coalgebra specs themselves are promoted under the same §12 rules (recursion terminates because a `CoalgebraSpecRecord` is not itself a coalgebra subject). | `tests/kernel/test_coalgebra_spec_required.rs`, `tests/kernel/test_coalgebra_adequacy_demotion.rs`, `tests/replay/test_behavioral_equivalence.py` |

## 16. Repository layout

```text
icf/
  docs/
    BUILD_SPEC.md                    # this file
    disa_stigs.json                  # STIG adapter input
    stig_list.csv                    # STIG adapter input
    critique.md                      # historical review notes
  core/                              # minimal trust kernel
    witness_core/
    evidence_core/
    pullback_core/
    falsifier_core/
    ledger_core/
    scope_core/
    kernel_primitives/               # hashing, signing, JCS (from icf-normative)
  training/
    critic_engine/
    breakfix_runner/
    witness_tester/
    counterexample_miner/
    survivor_model/
    residual_pool/
  synthesis/
    plan_generator/
    design_generator/
    program_synthesis/
    witness_proposer/
    revision_proposer/
    remediation_proposer/
  adapters/
    stig/
      src/
      docs/
        coverage-matrix.md           # regenerated here
      falsifier_library/
      break_operators/
      witnesses/                     # hand-authored starter witnesses
  experts/
    stig_expert_critic/
  sdk-py/                            # verification + attestation SDK
  schemas/
    record-envelope.schema.json
    records/                         # one schema per record kind in §6
  examples/
    demo/
      trust_root.toml                # mirror of current tip KeySetRecord
      site.toml
      sample_scan.log
      demo_keys/
  blobstore/
    demo/                            # content-addressed raw evidence
  ledgers/
    ACL.md                           # filesystem ACL profile (demo/prod)
    demo/                            # demo ledger slice
  tests/
    kernel/
    training/
    synthesis/
    adapters/
    replay/
    architectural/
  .github/workflows/ci.yml
  Cargo.toml
  rust-toolchain.toml
  deny.toml
  .gitignore
  README.md
```

## 17. Status of prior artifacts

| Artifact | Action | Destination |
| --- | --- | --- |
| `engine/crates/icf-normative` | Kept. | `core/kernel_primitives` (hashing, signing, canonical JSON). |
| `engine/crates/icf-audit` | Kept. | `core/ledger_core`, extended with batches and key-set history. |
| `engine/crates/icf-dsl` | **Retired.** | Replaced by typed witness families (§4.1). Source preserved in git history. |
| `engine/crates/icf-cli` | Kept, renamed to `icf`. | Top-level entry point; subcommands `verify`, `ledger verify`, `train`, `metrics`, `adapter stig …`. |
| `sdk-py/` | Kept. | Read/verify/attest SDK for every record kind in §6. |
| `schemas/record-envelope.schema.json` | Kept, extended. | Plus per-record schemas under `schemas/records/`. |
| `examples/demo/` | Kept. | Demo trust root mirror, demo ledger slice, demo blob store. |
| `docs/disa_stigs.json`, `docs/stig_list.csv` | Kept. | STIG adapter inputs. |
| `docs_bad_design/` | Left alone. | User-managed quarantine. |
| Any prior `docs/coverage-matrix.md` | Regenerated. | `adapters/stig/docs/coverage-matrix.md`. |

Migration PRs must preserve ledger content addressability; any record format change requires a new `schema_version` and a migration test.

## 18. Build phases and exit gates

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| **P0a — Falsifier walking skeleton** | End-to-end `pullback → PASS_WITH_FALSIFIER → non-vacuous falsifier template → batch commit → ledger verify` on one trivial STIG control; 1 hand-authored witness in family `FieldEquality`. | Demo CLI prints a verifiable ledger slice; `icf ledger verify` exits 0; E7 test green. |
| **P0 — Kernel** | All six `core/` modules; envelope + chain; scope registry; admission context; batch semantics; key-set history; checkpoint records; blob store interface; 2-of-2 promotion verification. | E1, E2, E4, E6, E7, E8, E10, E11 tests green; demo ledger round-trips byte-identically (§7); tamper test detects truncation. |
| **P1 — Training engine** | `critic_engine`, `breakfix_runner` with operator partitions, `witness_tester`, `counterexample_miner`, `survivor_model`, `residual_pool`; criticism lifecycle; evaluation-operator enforcement. | E5, E12 tests green; a contrived coarse witness is demoted by `witness_tester`; promotion candidate threshold demonstrated; `validated_criticism_yield` populated. |
| **P2 — Synthesis** | All `synthesis/` modules; proposal retraction flow. | E3 test green; no synthesis crate can construct `PromotionCandidateRecord` or `PromotionRecord`; replay fidelity holds across training runs seeded by synthesis. |
| **P3 — STIG adapter** | `adapters/stig` with ≥ 10 interpretable claims from the coverage matrix; starter witnesses across `FieldEquality`, `FieldPredicate`, `EvidencePresence`; falsifier library; training + evaluation break operators; level_instantiation `{behavior, world}`. | Adapter round-trip on demo F5 fixture; reconciler surfaces at least one synthetic adjacent-level contradiction in the test harness (seeded by a second latent level enabled for the test). |
| **P3b — Coalgebraic walking skeleton** | `CoalgebraSpecRecord` for the STIG expert critic filled across C1–C7; positive + negative `BehavioralEquivalenceRecord` pair; non-vacuous `CoalgebraAdequacyRecord` demonstration; refused-promotion demonstration per §25.5. | E13 test green; `coalgebra_adequacy_fire_rate` baseline recorded; the four §25.5 artifacts present in the demo ledger. |
| **P4 — Expert packaging** | `experts/stig_expert_critic` populated from survivor-state; expert bundle CLI; retirement flow. | Bundle is verifiable offline with only trust-root history, bundle, and blob store; `replay_fidelity == 1.0`; first expert promotion cites a `promoted` `CoalgebraSpecRecord`. |

Phases are sequential; skipping a gate is not allowed.

## 19. Test categories and phase mapping

| Category | What it proves | Gates phase |
| --- | --- | --- |
| Kernel | Witness schema enforcement, pullback determinism, falsifier non-vacuity, append-only, scope required, batch/commit semantics, dependency-state binding, 2-of-2 promotion. | P0a, P0, P1 |
| Architectural | Module boundaries (E1–E3, E9, E10); no forbidden imports; constructor visibility. | P0, P2 |
| Adversarial witness | Coarse / hidden-failure / version-drift witnesses behave per §11. | P1 |
| Break/fix training | Breaks detected; fixes do not create silent new failures; evaluation-operator survival enforced before promotion. | P1 |
| Synthesis isolation | No synthesis code path reaches `PromotionCandidate` or `Promotion`. | P2 |
| Multi-level contradiction | Reconciler detects seeded contradictions; `ContradictionRecord` emitted. | P3 |
| Adapter | Domain claims round-trip through §9's runtime loop on real and fixture evidence. | P3 |
| Replay | `payload_sha256` and `record_hash` recomputed byte-identically from ledger + key-set history + blob store. | P0, P4 |
| Coalgebraic production | C1–C7 schemas present; behavioral-equivalence oracle round-trip (both directions); non-vacuous adequacy fire demotes; E13 refuses unspecified-subject promotion. | P3b, P4 |
| Metrics | Truth-seeking metric non-regression (§14.1); cost-metric soft gate (§14.2). | P1 onward |

CI `.github/workflows/ci.yml` runs all categories; phase gates are enforced by required checks on PRs labeled with the target phase.

## 20. STIG specialization mapping

| Universal term | STIG v0.1 instance |
| --- | --- |
| Claim | Interpreted STIG control (from `docs/disa_stigs.json` by V-ID). |
| Evidence | iControl REST responses, `tmsh` output via REST, UCS metadata, syslog samples. Raw bytes in `blobstore/`; metadata in `EvidenceRecord`. |
| Witness | Per-control comparison model in one of `{FieldEquality, FieldPredicate, EvidencePresence}`. |
| Validator | Rust closure compiled from the witness family + the site-parameter bindings; hashed and recorded as `ValidatorRecord`. |
| Pullback | Compliance judgment for the V-ID in the declared TMOS scope. |
| Break | Targeted misconfiguration via `tmsh` over REST in a lab BIG-IP; partitioned training/evaluation/adversarial. |
| Fix | Reversion using the adapter's remediation recipe (human-gated; v0.1 does not auto-remediate). |
| Survivor-state | Per-control evidence that the witness detected each seeded misconfiguration on ≥ K environment axes (TMOS minor version, platform family, HA topology). |
| Expertise | 2-of-2 promoted survivor-state bundled into `experts/stig_expert_critic`. |

The coverage matrix (`adapters/stig/docs/coverage-matrix.md`) informs **which** controls are candidate for automated witnesses; it does not decide alignment.

## 21. Open questions (deferred)

Items explicitly not decided in v0.1. Each must be closed before v0.2 unless noted.

- **OQ-1** Threshold tuning. `N`, `K`, `EVAL_BREAKS_REQUIRED` defaults require a calibration study on the STIG domain.
- **OQ-2** Distributed ledger writes. v0.1 is single-writer.
- **OQ-3** Criticism retraction. Promoted to v0.1; workflow defined via `CriticismRecord.status` transitions; specific "who can retract" policy still to close.
- **OQ-4** Automated remediation. v0.1 `remediation_proposer` emits proposals only; the human-gated STIG remediation pipeline from the prior design is not yet reconnected.
- **OQ-5** Cross-version witness equivalence. Reclassified: the mechanism is `BehavioralEquivalenceRecord` (§6, §25.3). The remaining deferred question is only *which* oracle-input set generators are accepted and who signs them. Target: v0.2.
- **OQ-6** Cross-adapter ordering. Adapter-supplied monotonic counters only; vector clocks or Lamport scheme deferred.
- **OQ-7** Read-model projection (indexed queries over the append-only log) for operational efficiency.
- **OQ-8** KMS/HSM integration for signing keys and blob-cipher policy.
- **OQ-9** Additional witness families (`StateMachineConformance`, `RateOrThreshold`, `BoundaryRelation`). Required before any non-STIG adapter is considered credible.
- **OQ-10** Cross-domain maturation validation. §1.4 and §25.4 require the maturation coalgebra to be re-validated in each new domain, not merely assumed universal. The per-domain validation protocol (sample sizes, required diversity of `CoalgebraAdequacyRecord` injections during meta-level training, and minimum distinct adapters) is deferred to v0.2.

## 22. Shortest truthful statement

```text
Reality  <-  Evidence  <-  Witness  <-  Claim
Break → Criticize → Fix → Survive → Promote (2-of-2)
Falsifier required, typed, non-vacuous.
Object coalgebra specified (C1–C7), meta coalgebra falsifiable.
Failure preserved. Anchors external. Optimization earns its keep only in criticism.
```

## 23. Genesis

At system start there are no promoted artifacts. The bootstrap event must grant initial trust without violating "no trusted witness" in the long run.

### 23.1 Genesis procedure

1. Two independent holders of `genesis`-role keys assemble the initial `KeySetRecord` defining all non-genesis roles and their keys.
2. The genesis holders sign a `BootstrapAttestationRecord` whose payload includes:
   - the initial `KeySetRecord` hash,
   - the hashes of the initial witness family registrations (which witness families are kernel-enabled at launch),
   - the hashes of the initial `WitnessRecord` set shipped by the STIG adapter,
   - a mandatory "sunset clause": the genesis keys must rotate out via a future `KeySetRecord` within a declared interval.
3. The `BootstrapAttestationRecord` is the first chained record; its `prev_hash` is `null`. Every later record derives from it.

### 23.2 Trust grant and sunset

- Initial witnesses enter at `under_criticism`, **not** `provisional_survivor`. They earn status the normal way.
- Initial validators are recorded with `signer_role = "genesis"` and must be re-signed by `validator_author` keys before they can be cited by a `PromotionCandidateRecord`.
- The sunset clause makes genesis authority bounded: after the declared interval, any pullback or survivor update that still transitively depends on genesis-only-signed artifacts is marked `training_only = true`.

### 23.3 Reviewer guidance

A reviewer verifying an expert bundle must:

1. Verify the `BootstrapAttestationRecord` signatures against a trusted out-of-band copy of the two `genesis` public keys.
2. Walk `KeySetRecord` history from genesis to the tip.
3. Replay the chain under historical key sets.
4. Confirm that no `PromotionRecord` in the bundle depends transitively on genesis-only-signed artifacts.

## 24. Witness authoring workflow

Witness authoring is the likely labor center of the factory. v0.1 establishes the pipeline explicitly; scale is a v0.2 concern.

### 24.1 Lifecycle

```text
draft → family_selection → adapter_proposal → witness_tester_attack
      → survivor_accumulation → promotion_candidate → 2-of-2 promotion
      → in_service → retirement
```

- **draft**: authored locally from a family template; not yet in the ledger.
- **adapter_proposal**: submitted as `SynthesisProposalRecord { kind = witness }` with a draft `WitnessRecord`.
- **witness_tester_attack**: `witness_tester` runs coarseness / hidden-failure / version-drift probes. Failures produce `CriticismRecord` drafts.
- **survivor_accumulation**: `breakfix_runner` + `counterexample_miner` drive `SurvivorUpdateRecord`s.
- **promotion_candidate** / **promotion**: §12.
- **in_service**: the witness is admissible for new pullbacks.
- **retirement**: `WitnessRetirementRecord` marks the witness no longer admissible for new pullbacks; historical pullbacks remain valid; an optional successor witness is cited.

### 24.2 Templates

Each witness family ships a template under `adapters/<domain>/witnesses/templates/`. For the STIG adapter, every coverage-matrix row classified `AUTOMATED_CANDIDATE` gets an auto-generated draft keyed by its likely family.

### 24.3 v0.1 target

- 3–5 hand-authored starter witnesses across `FieldEquality`, `FieldPredicate`, `EvidencePresence`, exercising the full lifecycle end-to-end.
- ≥ 1 retirement + successor demonstration in the test harness.
- The rest of the coverage matrix ships as drafts, not as admissible witnesses.

## 25. Coalgebraic formulation and production test

This section makes the factory's structure explicit and subjects the specification itself to the same seven-part test it will apply to every candidate object-level expert. The formulation is descriptive of the architecture defined in §§3–16; it does not introduce independent behavior. Where it names functions already defined elsewhere (e.g., `pullback_core::pullback`, `survivor_model::propose_promotion`), those are the normative definitions; this section only states them as coalgebraic steps.

### 25.1 Two levels

- **Object-level coalgebra.** A candidate expert (e.g., the STIG expert critic) is a coalgebra whose state is the set of survivor-state plus admitted witnesses/validators it currently depends on, whose events are ledger-admitted inputs (evidence, claims, criticism, break operators), and whose observations are the records it emits (`PullbackRecord`, `CriticismRecord`, `FalsifierRecord`, `SurvivorUpdateRecord`).
- **Maturation coalgebra.** The factory (kernel + training + synthesis + survivor model + promotion protocol) is itself a coalgebra whose state is the multiset of object-level coalgebra specs at each lifecycle status, whose events are completed pullbacks / criticisms / break-fix cycles / counterexample finds / sufficiency decisions, and whose observations are the promotion, demotion, and retirement records it emits.

Both levels are declared operationally. Both must pass the C1–C7 test in §25.4.

### 25.2 Object-level coalgebra (the expert critic)

Formal surface (logical, not a new runtime type):

```text
CriticCoalgebraState =
    { coalgebra_spec_hash,             // CoalgebraSpecRecord this state is under
      admitted_witness_hashes,         // set<WitnessRecord hash, state=promoted-or-under-scope>
      admitted_validator_hashes,       // set<ValidatorRecord hash>
      survivor_state,                  // content-addressed survivor-state bundle
      open_criticisms,                 // set<CriticismRecord hash in status != validated>
      open_falsifiers,                 // set<FalsifierRecord hash with fired=true not yet demoted>
      ledger_tip_hash }                // monotone, equal to the enclosing AdmissionContext.ledger_tip

CriticEvent =
    | AdmitInput(ClaimRecord | EvidenceRecord | CriticismRecord)
    | RunPullback(claim_hash, evidence_set_hash, witness_hash, validator_hash, batch_id)
    | IngestFalsifier(FalsifierRecord)
    | ApplyBreakOperator(BreakRecord partition ∈ {training, evaluation, adversarial})
    | ApplyFix(FixRecord)
    | UpdateSurvivor(SurvivorUpdateRecord)
    | RetireWitness(WitnessRetirementRecord)

step_critic : CriticCoalgebraState × CriticEvent → CriticCoalgebraState × Observation*
```

`step_critic` is not new code. It is the deterministic composition of the already-specified kernel and non-kernel layer calls under one batch, governed by `pullback_core::pullback`, `survivor_model` updates, and the dependency-state binding rules in §11. Replay is already guaranteed by §7; that replay is the canonical definition of `step_critic`.

The `CoalgebraSpecRecord` required by E13 is the first-class declaration of each bulleted component:

| C-ref | `CoalgebraSpecRecord` field | Meaning |
| --- | --- | --- |
| C1 state | `state_schema_hash` | Hash of a JSON schema defining `CriticCoalgebraState`. |
| C2 observations | `observation_schema_hash` | Hash of the allowed observation record kinds and shapes. |
| C3 events | `event_schema_hash` | Hash of the allowed event record kinds and shapes. |
| C4 behavior | `step_identifier` | Symbolic reference to the kernel version that defines `step_critic`, pinned by kernel build hash. |
| C5 distinction | `distinction_oracle_ref` | Reference to a `BehavioralEquivalenceRecord` oracle-input set used to decide when two specs are equivalent under this witness set. |
| C6 falsifier | `adequacy_falsifier_ref` | The canonical `CoalgebraAdequacyRecord` template that would falsify the spec (see §25.3). |
| C7 scope | `scope` | Declared scope (identical shape to §4.6 scope). |

### 25.3 Meta-level coalgebra (the factory)

Formal surface:

```text
MaturationState =
    { key_set_history_tip,             // KeySetRecord chain head
      coalgebra_specs : map<hash, status>,
      witnesses : map<hash, status>,
      validators : map<hash, status>,
      open_promotion_candidates,
      sufficiency_overrides,
      ledger_tip_hash }

MaturationEvent =
    | IngestCoalgebraSpec(CoalgebraSpecRecord)
    | IngestSurvivorUpdate(SurvivorUpdateRecord)      // for any monitored subject
    | IngestCounterexample(BreakRecord from evaluation | adversarial)
    | IngestCriticismValidation(CriticismValidationRecord)
    | ProposeCandidate(PromotionCandidateRecord)       // survivor_model half
    | CoSignPromotion(PromotionRecord)                 // human_promoter half
    | ObserveAdequacyViolation(CoalgebraAdequacyRecord)
    | DemoteOnTrigger(DemotionRecord)

step_maturation : MaturationState × MaturationEvent → MaturationState × Observation*
```

`step_maturation` is likewise the composition of existing calls: `survivor_model::propose_promotion` (gated by §12 and E13), `verify_chain`'s promotion and demotion rules (E5, E11, E12, E13), and `scope_core::verify_axis_coverage`. No new runtime is added.

**Falsifiers for the maturation coalgebra.**

- `CoalgebraAdequacyRecord` against any `CoalgebraSpecRecord` falsifies the object-level specification *and* is a meta-level signal that the factory promoted (or was about to promote) an inadequate object. Its presence above a declared rate threshold on `coalgebra_adequacy_fire_rate` (§14.1) demotes the factory build itself back to `under_criticism` status for the affected domain. This is the concrete meta-level falsifier demanded by the critique.
- `BehavioralEquivalenceRecord` failures — two specs asserted distinct that turn out indistinguishable on the oracle-input set, or vice versa — are meta-level criticism against the distinction test itself.

### 25.4 The Coalgebra Production Test (C1–C7)

Every candidate object-level coalgebra must, before promotion, answer all seven:

1. **C1 State.** A closed schema for `CriticCoalgebraState` with no free variables. Pinned by `state_schema_hash`.
2. **C2 Observations.** A closed enumeration of observation record kinds it may emit. Any attempt to emit an out-of-enumeration record is a C6 adequacy failure.
3. **C3 Events.** A closed enumeration of event kinds it accepts. Out-of-enumeration events are rejected at admission; a silent drop is a C6 failure.
4. **C4 Behavior.** A deterministic `step_critic` pinned to a kernel build hash, demonstrated by passing the replay suite (§7) at `replay_fidelity == 1.0`.
5. **C5 Distinction.** A signed oracle-input set on which this spec is behaviorally distinct from the nearest declared sibling spec under the same witness set. Recorded as `BehavioralEquivalenceRecord` with `equivalent = false` on the intended witnesses and `equivalent = true` on any deliberately shadowed witnesses.
6. **C6 Falsifier.** A declared `CoalgebraAdequacyRecord` template describing what concrete divergence would demote the spec, and proof that the template is non-vacuous (a synthetic divergence in a test harness actually fires it).
7. **C7 Scope.** A declared scope identical in shape to §4.6, enforced by `scope_core`.

The same seven questions apply to the maturation coalgebra. Its C1–C3 are `MaturationState`, the observation set of records it emits (`PromotionCandidateRecord`, `PromotionRecord`, `DemotionRecord`, `SufficiencyRecord`, `WitnessRetirementRecord`, `CheckpointRecord`, `KeySetRecord`), and the `MaturationEvent` enumeration. C4 is `step_maturation` pinned to the kernel build hash. C5 is the behavioral-equivalence protocol applied across factory builds: two factory builds are equivalent on a declared oracle-input set of chains iff they emit the same promotion/demotion sequence. C6 is the `coalgebra_adequacy_fire_rate` regression gate plus failed `BehavioralEquivalenceRecord`s. C7 is §1.4 plus OQ-10: structural universality plus per-domain re-validation.

### 25.5 Minimum factory walking skeleton for coalgebraic validation

Before any expert bundle can be promoted, the repository must demonstrate, in the demo ledger:

1. One `CoalgebraSpecRecord` for the STIG expert critic, filled out across C1–C7.
2. A `BehavioralEquivalenceRecord` between two trivial validator variants implementing the same `FieldEquality` witness, asserting `equivalent = true` on a declared oracle-input set (positive case) and a second asserting `equivalent = false` between a `FieldEquality` and a `FieldPredicate` over the same observable (negative case).
3. A deliberately-broken validator variant that provokes a `CoalgebraAdequacyRecord` (non-vacuity demonstration for C6), followed by the corresponding `DemotionRecord`.
4. A `PromotionCandidateRecord` that is correctly *refused* by `survivor_model` because the enclosing `CoalgebraSpecRecord` is not yet `promoted` (E13 demonstration).

Only after all four artifacts appear in the demo ledger is the STIG expert bundle eligible for its first promotion.

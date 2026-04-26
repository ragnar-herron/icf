STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---

# Maturity Production Backlog

The demo maturity gate now passes for all 47 rows (41 structural C/P/M/E/D + 6 L live-evidence rows from the real-device break/fix run and the full 67-control live campaign against `bigip1` at `132.145.154.175`):

```text
Demo-pass rows: 47
Partial rows:   0
Fail rows:      0
Demo maturity gate: PASS
```

Re-check at any time:

```powershell
cargo run -- maturity report --partials-only
cargo run -- maturity report --fail-on-partial
```

Both commands exit 0 today. If any row is ever flipped back to `partial` (or any of the five audit tests fail), `--fail-on-partial` exits non-zero.

## Audit wiring that closes the previously-partial rows

| Row | Evidence closed by | Audit test |
| --- | --- | --- |
| **M4** Scope Expansion | `coalgebra/stig_expert_critic/ScopeCoverageMatrix.json` derived from `docs/stig_list.csv` × `docs/disa_stigs.json` (67 controls, 5 modules, 3 surfaces, 2 automation classes, 3 severities) | `tests/audit.rs::m4_scope_coverage_matrix_is_multi_axis_and_traceable` |
| **D1** Core Pullbacks Preserved | `coalgebra/stig_expert_critic/PullbackBaseline.json` (P1–P10 with required evidence keywords) | `tests/audit.rs::d1_core_pullbacks_preserved` |
| **D4** Stable Maturation Logic | `coalgebra/stig_expert_critic/MaturationLogicStability.json` with `cross_domain_test_status: "passed"` | `tests/audit.rs::d4_stable_maturation_logic_on_second_domain` (runs the kernel maturation suite on a second synthetic domain `demo.ntp.synchronized`) |
| **D6** Metric Integrity | `coalgebra/stig_expert_critic/MetricSignature.json` + `ledgers/demo/metric_checkpoint.jsonl` (SHA-256 commit + checkpoint anchor) | `tests/audit.rs::d6_metrics_match_signed_digest_and_checkpoint` |
| **D8** General vs Specialized Separation | `docs/BUILD_SPEC.md` §25 + audit test | `tests/audit.rs::d8_kernel_is_domain_agnostic` (forbids STIG-domain tokens in `src/model.rs` / `src/ledger.rs`) |

## Longitudinal demo evidence (unchanged)

The two-revision fixture still covers `M2`, `M3`, `M5`, `M6`, `M7`, `E1`, `E2`, `E5`, `E6`, and `E7`:

```powershell
cargo run -- maturity verify-fixture fixtures\maturity
```

Those rows remain `demo-pass`, not production-pass. Production promotion still requires real STIG time-series evidence from a lab.

## Production-only gaps (declared in artifacts; do NOT block the demo gate)

These are explicitly declared in the corresponding artifacts as things that must change before any production claim. They are tracked as "production_gap" fields so promotion reviewers can find them mechanically:

- **M4** — Every `AUTOMATED_CANDIDATE` in the coverage matrix still owes its own witness-authoring, break/fix, and promotion cycle in a real lab before being called "covered".
- **D1** — The pullback baseline lives in-repo. Production wants a signed baseline + cross-revision release-train audit.
- **D4** — Only one additional synthetic domain is exercised. Production requires at least three real adapters with lab evidence each.
- **D6** — Demo signature is SHA-256 content commit. Production requires Ed25519 signing by the trust root and cross-posting the checkpoint to an external append-only notary (per `BUILD_SPEC.md` §6 `KeySetRecord` / §5.4 `CheckpointRecord`).
- **D8** — The kernel check enforces no STIG tokens in `src/model.rs` / `src/ledger.rs`. Production should extend the rule to an explicit crate / visibility boundary (e.g., a separate `icf-kernel` crate) enforced at compile time.
- **Live (L1–L6)** — One device and one topology are now covered by two replayable ledgers: `ledgers/live/break_fix.jsonl` and `ledgers/live/full_campaign.jsonl`. The latest closeout rerun tightened discovery and reduced the live campaign to **54 pass / 2 fail / 5 not-applicable / 6 blocked-external**. `coalgebra/stig_expert_critic/LiveCampaignEvidence.json.production_gaps_live` now concentrates the remaining live-production gaps on TLS fingerprint pinning, token-based auth with rotation, multi-device / multi-topology coverage, external dependency closure for the six blocked rows, approved device-certificate replacement, always-on VPN enforcement for the remaining remote-access failure, clustered save-config and config-sync verification, and change-management-gated disruptive remediation.

STATUS: SUPERSEDED BY docs/canonical/CANONICAL_GATE_SUITE.md
DO NOT USE AS BUILD AUTHORITY

---


# Maturity Test Set

A design passes only if it can answer these questions with explicit mechanisms, records, and tests.

| ID | Test                             | What it checks                                                                            | Pass condition                                                                       | Fail means                            |
| -- | -------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------- |
| M1 | **State Growth Test**            | Can the system represent richer survivor-state over time without collapsing distinctions? | Later states preserve earlier criticism/evidence and add structured survivor updates | “Learning” is just overwrite          |
| M2 | **Criticism Retention Test**     | Are criticisms preserved and reusable?                                                    | Prior criticisms remain replayable and linked to later promotions/demotions          | System forgets why it changed         |
| M3 | **Falsifier Vitality Test**      | Does the system keep producing real falsifiers?                                           | Nonzero falsifier yield over meaningful windows                                      | System has become self-confirming     |
| M4 | **Scope Expansion Test**         | Can the system mature across broader declared scope?                                      | Surviving rules cover more valid scope points without hidden regressions             | System only looks mature in a sandbox |
| M5 | **Survivor Strength Test**       | Are promoted survivors actually becoming stronger?                                        | Promotions survive over time and across varied axes; demotion rate is controlled     | Promotion is decorative               |
| M6 | **Witness Adequacy Growth Test** | Are witnesses improving under criticism?                                                  | Witness revisions reduce hidden-failure misses and improve counterexample detection  | Bottleneck exists but stays weak      |
| M7 | **Efficiency Honesty Test**      | Is wasted work decreasing without truth loss?                                             | waste_heat_ratio improves while falsifier yield and criticism yield do not regress   | System is optimizing away truth       |
| M8 | **Recursive Reopening Test**     | Can promoted artifacts be reopened under new evidence?                                    | New criticism/falsifier can demote prior survivors                                   | System hardens into dogma             |

---

# Progressive Error-Correction Test Set

This section tests whether the system does more than store records — it must actually **correct errors over time**.

| ID | Test                                            | What it checks                                                               | Pass condition                                                                                      | Fail means                                |
| -- | ----------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| E1 | **False Positive Reduction Test**               | Does the rate of false passes decrease?                                      | Across comparable windows, false positives trend downward                                           | Passing is not becoming more truthful     |
| E2 | **False Negative Reduction Test**               | Does the rate of false fails decrease?                                       | Across comparable windows, false negatives trend downward                                           | System remains brittle or over-strict     |
| E3 | **Break Detection Progress Test**               | Does the system get better at detecting seeded breaks?                       | Counterexample/break detection rate improves or holds under wider scope                             | Critic is not learning from break/fix     |
| E4 | **Fix Validation Progress Test**                | Does it get better at distinguishing true fixes from fake fixes?             | Post-fix regressions fall; failed fixes are caught earlier                                          | Remediation advice is not improving       |
| E5 | **Synthesis Correction Test**                   | Do synthesized proposals improve under criticism?                            | Rejection reasons cluster into learnable improvements; survivor rate rises without truth regression | Synthesis is churning, not learning       |
| E6 | **Witness Miss Reduction Test**                 | Do witness-hidden failures decrease over time?                               | Adversarial witness tests produce fewer missed failures                                             | Core comparison surfaces stay immature    |
| E7 | **Adjacent-Level Contradiction Reduction Test** | Do cross-level inconsistencies become better represented and reduced?        | Contradictions are detected earlier and unresolved contradiction backlog shrinks                    | Multi-level planning is not cohering      |
| E8 | **Residual Conversion Test**                    | Does unexplained residual evidence get turned into new witnesses/criticisms? | Residual pool items increasingly become explicit witness proposals or criticisms                    | “Waste heat” is just garbage accumulation |

---

# Anti-Drift Test Set

This is the critical section for your concern about continuously adjusting the universal constructor.

| ID | Test                                       | What it checks                                                                  | Pass condition                                                                                                                                                                                       | Fail means                                             |
| -- | ------------------------------------------ | ------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| D1 | **Core Pullback Preservation Test**        | Are the core pullbacks preserved?                                               | Declaration–Reality, Claim–Evidence, Witness–Reality, Plan–Execution, Synthesis–Behavior, Failure–Survivor, Level–Level, Revision–Identity, Criticism–Memory, Optimization–Truth all remain explicit | The constructor’s heart is drifting                    |
| D2 | **Identity Boundary Test**                 | Are revisions checked against stable task identity?                             | Non-constitutive changes preserve the declared identity boundary                                                                                                                                     | Improvement is actually redesign                       |
| D3 | **Constitutive Revision Declaration Test** | Does the system explicitly mark redesign when it occurs?                        | Any change to core pullbacks, witness family laws, or promotion law is declared as constitutive revision                                                                                             | Drift is hidden as “refinement”                        |
| D4 | **Stable Maturation Logic Test**           | Does the same promotion/demotion logic apply across domains?                    | General maturation coalgebra remains stable while domain object coalgebras vary                                                                                                                      | New domains force redesign of the maturation machine   |
| D5 | **Lineage Preservation Test**              | Can every survivor trace back to its criticisms and predecessors?               | Complete ancestry is replayable after refactor or optimization                                                                                                                                       | Refactoring causes epistemic amnesia                   |
| D6 | **Metric Non-Corruption Test**             | Are maturity metrics prevented from becoming the objective in a corrupting way? | No optimization passes if falsifier yield, replay fidelity, or criticism power regress                                                                                                               | Metrics are being gamed                                |
| D7 | **No Shortcut Closure Test**               | Are there any new direct comparison paths bypassing witnesses?                  | Static and dynamic tests show all judgments still route through pullback                                                                                                                             | CORBA-style collapse has returned                      |
| D8 | **General-vs-Specialized Separation Test** | Is the meta-coalgebra stable while object coalgebras specialize?                | Domain-specific change does not alter the general maturation constitution                                                                                                                            | Universality is fake; each domain rebuilds the machine |

---

# Required Metrics Behind the Tests

These tests should be computed from a small **maturity metric stack**.

## Core metrics

| Metric                     | Meaning                                                     |
| -------------------------- | ----------------------------------------------------------- |
| `false_positive_rate`      | fraction of passes later falsified                          |
| `false_negative_rate`      | fraction of fails later shown to be valid                   |
| `falsifier_yield`          | falsifiers produced per relevant pullback/trial             |
| `criticism_yield`          | criticisms produced per relevant pullback/trial             |
| `counterexample_rate`      | breaks detected / breaks injected                           |
| `post_fix_regression_rate` | fixes that introduce new failure / fixes attempted          |
| `survivor_retention_rate`  | promoted survivors remaining valid over time                |
| `scope_coverage`           | survived scope points / declared relevant scope points      |
| `residual_conversion_rate` | residual items turned into new witness/criticism structures |
| `replay_fidelity`          | fraction of replayed records exactly reproduced             |
| `waste_heat_ratio`         | wasted work / useful truth work                             |
| `identity_stability_rate`  | non-constitutive changes / total changes                    |

---

# Pass/Fail Gates

Now make it operational.

## Gate A — Maturity

The design is maturity-capable only if:

* M1–M8 all pass
* `replay_fidelity = 1.0`
* `survivor_retention_rate` is nontrivial and improving or stable
* `scope_coverage` is increasing honestly

## Gate B — Progressive Error Correction

The design is progressively error-correcting only if:

* E1–E8 all pass
* `false_positive_rate` and `false_negative_rate` do not regress over agreed windows
* `counterexample_rate` and `criticism_yield` do not collapse
* post-fix validation is closing the loop

## Gate C — Anti-Drift

The design is anti-drift only if:

* D1–D8 all pass
* `identity_stability_rate` stays above threshold
* every constitutive change is explicitly declared
* no new witness-bypass path appears

If Gate C fails, the system may still be learning, but it is not stably maturing the same universal constructor.

---

# Minimal Threshold Version

If you want a compact threshold set, use this:

| Metric                     | Minimum condition                                                    |
| -------------------------- | -------------------------------------------------------------------- |
| `replay_fidelity`          | exactly `1.0`                                                        |
| `falsifier_yield`          | `> 0` and non-regressing                                             |
| `criticism_yield`          | `> 0` and non-regressing                                             |
| `counterexample_rate`      | non-regressing                                                       |
| `false_positive_rate`      | non-increasing                                                       |
| `false_negative_rate`      | non-increasing                                                       |
| `post_fix_regression_rate` | non-increasing                                                       |
| `scope_coverage`           | non-decreasing                                                       |
| `survivor_retention_rate`  | non-decreasing after promotion window                                |
| `waste_heat_ratio`         | non-increasing without truth regression                              |
| `identity_stability_rate`  | above declared threshold, e.g. `>= 0.9` for non-constitutive updates |

These are not universal laws, but they are good starting gates.

---

# Recursive Use

Use this test set recursively at three levels:

## 1. Object level

Example:

* STIG expert critic
* spreadsheet analyst expert
* robot manipulation expert

Ask: does this domain expert mature, error-correct, and remain stable?

## 2. Expert bundle level

Ask: does the promoted bundle keep improving without drifting?

## 3. Meta-coalgebra level

Ask: does the system that matures experts itself mature without redesigning its constitutional core?

This is the most important one.
A universal constructor fails if the meta-level passes improvements by changing its own heart every cycle.

---

# Strongest Rule

Here is the cleanest anti-drift rule:

## A change is a refinement only if it improves one or more maturity/error-correction metrics without failing any anti-drift test.

Otherwise it is a constitutive redesign.

That gives you a hard classification mechanism.

---

# One-Page Review Form

You can use this in design review:

| Category                             | Pass/Fail    | Evidence |
| ------------------------------------ | ------------ | -------- |
| Maturity Gate A                      | ☐ / ☐        |          |
| Error-Correction Gate B              | ☐ / ☐        |          |
| Anti-Drift Gate C                    | ☐ / ☐        |          |
| Constitutive redesign required?      | ☐ yes / ☐ no |          |
| If yes, which core pullback changed? |              |          |

---

# Short anchor

**The design is successfully maturing only if truth improves, criticism power holds or rises, survivors strengthen across scope, waste falls honestly, replay remains exact, and the same core pullback constitution survives revision.**


run docs/info_maturity_score_v2.md with canvas and report the score
# 🔒 **Distinction-Preserving Maturity Test v2 (Complete Rewrite)**

## 1. Core Objective

The system must **only pass** if:

```text
Every pullback preserves the exact lawful distinction it claims to measure,
under adversarial falsifier pressure,
across all known representations,
with no loss of atomic truth.
```

Anything less = fail or blocked.

---

# 2. Hard Gates (Non-Negotiable)

These are **absolute invariants**. No score can override them.

## HG-1 — Replay Fidelity

```text
replay_fidelity == 1.0
```

## HG-2 — Distinction Integrity

```text
distinction_loss_rate == 0
```

Measured as:

```text
collapsed_distinctions / required_distinctions == 0
```

## HG-3 — Atomic Pullback

```text
atomic_integrity_score == 1.0
```

No composite, no noisy projections at comparison layer.

## HG-4 — Lawful Partition Validity

Every control must define and pass:

```text
{compliant, noncompliant, disabled, absent, malformed, indeterminate}
```

No collapse allowed.

## HG-5 — Falsifier Presence

```text
falsifier_pressure > 0
AND
falsifier_effectiveness > 0
```

## HG-6 — Known Bad Must Fail

All canonical bad fixtures MUST fail.

## HG-7 — Known Good Must Survive

At least one valid state must pass or remain provisionally valid.

## HG-8 — Representation Equivalence

```text
representation_coverage == 1.0
```

All known encodings normalize identically.

## HG-9 — Factory ↔ Export Equivalence

```text
factory_output == export_output
```

Byte-level or canonical equality.

## HG-10 — Identity Stability

```text
identity_stability_rate >= 0.95
```

---

# 3. Distinction Metrics (Scored Only If HG Pass)

## M1 — Partition Coverage

```text
>= 0.95
```

## M2 — Representation Coverage

```text
== 1.0
```

## M3 — Counterexample Detection

```text
>= 0.95
```

## M4 — Residual Conversion

```text
monotonically increasing
```

## M5 — Survivor Retention

```text
non-decreasing
```

## M6 — Fix Validation

```text
post_fix_regression_rate == 0
```

## M7 — Waste Heat (Constrained)

```text
may decrease ONLY IF distinction_loss_rate == 0
```

---

# 4. Mandatory Fixture Pack (Per Control)

Every control MUST include:

```text
good_minimal
bad_canonical
bad_representation_variant
boundary_value
disabled_state
absent_state
malformed_state
noisy_evidence
out_of_scope_variant
```

If any fixture class is missing → FAIL

---

# 5. Distinction-Preserving Tests

## T1 — Atomic Pullback Test

Input:

* noisy + atomic data

Pass:

* only atomic value used in comparison

Fail:

* any extra structure leaks into verdict

---

## T2 — Partition Separation Test

For each partition class:

* system must produce distinct outcomes

Fail:

* any collapse between:

  * disabled vs compliant
  * absent vs compliant
  * malformed vs pass/fail

---

## T3 — Representation Equivalence Test

For each encoding variant:

* normalized output must be identical

Fail:

* any divergence

---

## T4 — Known Bad Test

All bad fixtures:

```text
must_fail == true
```

---

## T5 — Known Good Test

At least one:

```text
may_pass == true
```

---

## T6 — Falsifier Activation Test

Inject adversarial inputs.

Pass:

* system produces new criticism or failure

Fail:

* system remains stable under attack

---

## T7 — Residual Capture Test

Unresolved must produce:

```text
explicit_residual_record == true
```

---

## T8 — Fix Validation Test

Apply fix:

Pass:

* failure disappears
* no new failures introduced

Fail:

* regression or false pass

---

## T9 — Export Equivalence Test

```text
factory == export
```

Fail:

* any difference

---

## T10 — Scope Honesty Test

Out-of-scope inputs must:

```text
return unresolved or out_of_scope
```

Fail:

* silent pass

---

# 6. Maturity Score (Only After HG Pass)

```text
maturity_score =
0.20 partition_coverage +
0.15 representation_coverage +
0.15 counterexample_detection +
0.10 residual_conversion +
0.10 survivor_retention +
0.10 fix_validation +
0.10 falsifier_effectiveness +
0.10 waste_efficiency
```

---

# 7. Status Classification

| Status            | Condition                          |
| ----------------- | ---------------------------------- |
| BLOCKED           | Any HG fails                       |
| TRAINING          | HG pass, score < 0.85              |
| PROMOTABLE        | HG pass AND score ≥ 0.85           |
| PLATEAUED         | no improvement + no new falsifiers |
| REDESIGN_REQUIRED | requires partition/pullback change |

---

# 8. Loop (Run-to-Truth)

```text
loop:
    measure metrics
    evaluate hard gates

    if any HG fails:
        status = BLOCKED
        fix HG violation
        continue

    run distinction tests (T1–T10)

    if any fail:
        generate criticism
        revise adapter / witness / partition
        continue

    compute maturity_score

    if score >= threshold:
        status = PROMOTABLE
        break

    if plateau:
        status = PLATEAUED
        break

    select next action:
        highest distinction gain without regression

    execute
```

---

# 9. Absolute Stop Rule

## 🔴 PRIMARY RULE

```text
NO CHANGE MAY IMPROVE SCORE
IF IT REDUCES DISTINCTION INTEGRITY
```

---

# 10. What This Fixes (Your Original Problem)

This version prevents:

* semantic adapter drift
* false equivalence (0 == compliant)
* noisy evidence passing as truth
* parser blind spots
* export divergence
* fake maturity through efficiency gains

Because:

## It blocks them BEFORE promotion

---

# 11. Final Guarantee

If this test passes:

```text
Every accepted evaluator preserves lawful distinctions,
is falsifier-tested,
is representation-complete,
and produces atomic, replayable truth.
```

---

# 🔑 Final Anchor

**This system does not measure how good the answers look.
It measures whether the system is incapable of collapsing real distinctions while producing those answers.**

---

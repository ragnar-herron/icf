STATUS: SUPERSEDED BY docs/canonical/CANONICAL_GATE_SUITE.md
DO NOT USE AS BUILD AUTHORITY

---

Yes.

You can make those failures **impossible by construction** only if the adapter is forced through a small set of **distinction-preserving pullback gates** before it is accepted, promoted, exported, or shipped.

Below is a concrete set you can add.

---

# Distinction-Preserving Pullback Gates

## Gate DP-1 — Measurable identity gate

**Question:** Does the evaluator measure the exact contract field, and only that field?

The adapter must declare:

* `contract_measurable_id`
* `runtime_source_path`
* `projection_fn`
* `atomic_value_type`

Pass only if:

* one contract measurable maps to one declared runtime source
* the projection function returns exactly one atomic comparison value
* no extra fields survive into the comparison surface

Fail if:

* the evaluator uses proxy fields
* multiple fields are silently aggregated
* unrelated payload structure is exposed

### Explicit falsifiers

* known-good fixture where target field exists but proxy field differs
* known-bad fixture where proxy field matches but true field fails

This kills:

* wrong-field measurement
* proxy-based false pass

---

## Gate DP-2 — Atomic pullback gate

**Question:** Is the observed value truly atomic in the same comparison space as the required value?

Every pullback row must have exactly:

* `required_atomic`
* `observed_atomic`
* `comparison_operator`
* `verdict`

No lists, blobs, or noisy structures are allowed on the final comparison row unless the contract explicitly defines a set-valued measurable.

Pass only if:

* the final comparison surface is irreducible for that contract
* any normalization is explicit and reversible to source evidence

Fail if:

* profile dumps, object graphs, or composite records appear where a scalar or atomic token is required
* comparison happens after hidden reduction steps

### Explicit falsifiers

* noisy evidence fixture that includes correct atomic value plus distracting extra fields
* evaluator must reject or normalize explicitly, not silently compare

This kills:

* non-atomic pullbacks
* noisy evidence masquerading as truth

---

## Gate DP-3 — Lawful distinction gate

**Question:** Does the predicate preserve the real operational distinction the STIG cares about?

For every contract measurable, define:

* `lawful_partition`

  * pass states
  * fail states
  * unresolved states

This is stronger than a numeric predicate.

Example:

* `idle_timeout <= 300` is not enough
* you must also declare `0 = disabled = fail`

Pass only if:

* the lawful partition matches actual operational behavior
* numeric or textual predicates do not collapse distinct runtime meanings

Fail if:

* two operationally different states land in the same pass class
* disabled and compliant collapse together
* absent and zero collapse together when they should not

### Explicit falsifiers

* one fixture for each boundary class:

  * compliant
  * noncompliant
  * disabled
  * absent
  * malformed
  * indeterminate

This kills:

* mathematically valid but operationally false predicates

---

## Gate DP-4 — Runtime representation equivalence gate

**Question:** Does the adapter correctly normalize all equivalent runtime encodings of the same violation or compliance state?

Example:

* port `0`
* `any`
* `.0`
* vendor-specific wildcard forms

The adapter must declare:

* `representation_equivalence_class`
* normalization rules
* unnormalized source examples

Pass only if:

* all known equivalent encodings map to the same atomic pullback value
* unknown encodings fail closed or go unresolved

Fail if:

* one representation passes and another equivalent one fails
* parser misses vendor-native variants

### Explicit falsifiers

* paired fixtures using equivalent encodings of the same bad state
* both must fail identically

This kills:

* parser blindness
* representation drift

---

## Gate DP-5 — Known-bad mandatory failure gate

**Question:** Does a canonical bad fixture for this exact control fail?

Every control must ship with at least one **must-fail fixture**.

Pass only if:

* known-bad runtime state fails at the final pullback row
* failure cites the exact lawful measurable

Fail if:

* bad fixture passes
* bad fixture becomes unresolved without declared reason

### Explicit falsifiers

* the fixture itself is the falsifier

This kills:

* clean-looking evaluators that never face real negative evidence

---

## Gate DP-6 — Known-good admissible pass gate

**Question:** Does a canonical good fixture pass or provisionally pass?

Every control must also ship with at least one **may-pass fixture**.

Pass only if:

* known-good state passes with attached falsifier
* or provisionally passes if witness is still under criticism

Fail if:

* good fixture fails for the wrong reason
* evaluator is so strict that it destroys valid distinctions

### Explicit falsifiers

* intentionally perturbed near-boundary good state that should flip outcome

This kills:

* overfit fail-always evaluators
* brittle contracts

---

## Gate DP-7 — Export equivalence gate

**Question:** Does the shipped/exported evaluator behave identically to the factory evaluator?

The factory and export must be compared over the same fixture pack.

Pass only if:

* same pullback rows
* same verdicts
* same unresolved classes
* same falsifier attachments
* same scope warnings

Fail if:

* export simplifies or reshapes the pullback
* export omits atomic distinctions
* export computes “equivalent-looking” but different results

### Explicit falsifiers

* fixture pack diff between factory and export
* any row mismatch fails shipping

This kills:

* “good factory / bad product” divergence

---

## Gate DP-8 — Scope honesty gate

**Question:** Is the evaluator promoted only for the runtime scope it actually survived?

Every adapter must declare:

* product/version
* module
* topology
* policy assumptions
* environment axes

Pass only if:

* promotion scope is bounded by tested fixtures
* untested representations remain out of scope or unresolved

Fail if:

* a control is promoted across versions or modules it never survived
* export implies broader coverage than evidence supports

### Explicit falsifiers

* out-of-scope fixture that the evaluator incorrectly treats as in-scope pass

This kills:

* scope inflation
* fake universality

---

## Gate DP-9 — Source anchoring gate

**Question:** Is every operational distinction traceable back to source STIG text and not invented downstream?

Every measurable must cite:

* source STIG clause
* adapter interpretation note
* runtime evidence path
* lawful partition rationale

Pass only if:

* you can trace the pullback row back to source requirement text and forward to runtime evidence

Fail if:

* distinction exists only in evaluator code
* source rationale is missing
* adapter silently introduces semantics

### Explicit falsifiers

* control where source requirement is ambiguous and evaluator still claims certainty

This kills:

* invented semantics
* adapter mythology

---

## Gate DP-10 — Unresolved honesty gate

**Question:** Does the evaluator fail closed into unresolved when atomic truth cannot be preserved?

Pass only if:

* ambiguous, missing, mixed, or noisy evidence becomes `INSUFFICIENT_EVIDENCE` or `WITNESS_UNDER_CRITICISM`
* never a silent pass/fail

Fail if:

* ambiguity is collapsed into confidence
* missing fields are interpreted as compliant defaults

### Explicit falsifiers

* truncated evidence fixture
* mixed representation fixture
* malformed payload fixture

This kills:

* false certainty
* convenience closure

---

# Required fixture pack per control

To make this real, every STIG control should carry a mandatory fixture pack:

* `good_minimal`
* `bad_canonical`
* `bad_representation_variant`
* `boundary_value`
* `disabled_or_null_state`
* `missing_evidence`
* `noisy_evidence`
* `out_of_scope_variant`

Not every control will use every fixture class the same way, but every class must be explicitly marked:

* required
* not applicable
* deferred with reason

---

# Promotion rule upgrade

An adapter/witness/evaluator may not be promoted unless all applicable distinction-preserving gates pass.

So promotion requires:

* DP-1 through DP-10 pass
* known-good and known-bad fixtures both behave correctly
* export equivalence holds
* no open criticism on lawful partition
* all unresolved cases are explicit and scoped

This changes the meaning of promotion from:

* structurally shaped
  to:
* distinction-safe

---

# Shipping rule upgrade

## No export ships unless factory and export pass the same fixture pack under the same distinction-preserving gates.

That makes:

* contract drift
* export simplification
* UI-side reinterpretation
* adapter mismatch

unshippable.

---

# Minimal record additions

Add these records if you do not already have them:

* `MeasurableBindingRecord`
* `LawfulPartitionRecord`
* `RepresentationEquivalenceRecord`
* `AtomicPullbackRowRecord`
* `FixtureExpectationRecord`
* `FactoryExportEquivalenceRecord`

These are the brick and mortar for the new gates.

---

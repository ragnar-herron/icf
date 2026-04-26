STATUS: SUPERSEDED BY docs/canonical/CANONICAL_GATE_SUITE.md
DO NOT USE AS BUILD AUTHORITY

---


---

# Coalgebra Production Test

A design passes this test only if it can answer all seven questions **explicitly and constructively**.

## C1. What is the state?

Can you name a canonical state space `X` for the system?

Not a vague description like “the current situation.”
It must be something like:

* witness registry state
* survivor/promotion state
* open criticism state
* scope state
* trust state
* domain model state

Pass condition:

* the design defines a stable state schema
* state is not confused with a log, rulebook, or output

Failure means:

* no coalgebra has really been produced

---

## C2. What is observable?

Can you name an observation space `O`?

A coalgebra must expose behavior.
For your systems, observations may be:

* judgments
* criticisms
* falsifiers
* promotions/demotions
* emitted records
* visible statuses
* output traces

Pass condition:

* the design defines what can be seen from a state without collapsing state into observation

Failure means:

* the system is not behaviorally defined

---

## C3. What changes the state?

Can you name the admissible input or event space `I`?

Examples:

* new evidence
* break injection
* fix application
* criticism validation
* synthesis proposal
* scope change
* trust-root change

Pass condition:

* the design defines which events drive state evolution

Failure means:

* there is no actual dynamical semantics

---

## C4. What is the behavior map?

Can you define a map of the form

[
c : X \to F(X)
]

or in operational form,

[
step : X \times I \to O \times X
]

or an equivalent coalgebraic form?

This is the core test.

Pass condition:

* the design gives a definite way to determine the next observable behavior and successor state from the current state and admissible input

Failure means:

* there is no coalgebra, only prose about behavior

---

## C5. What distinguishes two states behaviorally?

Can you define a test of behavioral distinction?

This need not be a metric. It can be:

* bisimulation distinction
* trace difference
* different judgments under same input
* different falsifier exposure
* different promotion behavior
* different criticism yield

Pass condition:

* the design says when two states are behaviorally the same or different

Failure means:

* “state” is untestable ornament

---

## C6. What falsifies the coalgebra claim?

Can you name what would show that the alleged coalgebra is wrong, too coarse, too fine, or behaviorally inadequate?

Examples:

* same claimed state yields different outputs under same input
* equivalent states fail bisimulation test
* observation map hides a failure the design says must be visible
* transition map cannot account for recorded ledger transitions
* promoted state behaves like under-criticism state with no observable distinction

Pass condition:

* the design includes explicit coalgebra falsifiers

Failure means:

* coalgebra is being asserted rather than tested

---

## C7. What is the scope of the coalgebra?

Can you declare the environment axes and validity range under which this coalgebra is supposed to model behavior?

Examples:

* STIG scope: TMOS version, platform family, HA topology
* spreadsheet scope: formula language, relational assumptions, workbook structure
* robot scope: embodiment, task family, sensor suite, environment class

Pass condition:

* the coalgebra has declared scope and can fail outside it

Failure means:

* “the coalgebra” is really an unscoped universal claim

---

# Pass criterion

A design **produces a coalgebra** if and only if it can answer all seven questions with:

* explicit schemas or types
* explicit behavior map
* explicit distinction test
* explicit falsifier
* explicit scope

That is the test.

---

# Compact proof idea

Why does this test work?

Because a coalgebra is not merely “something dynamic.” It is a structure whose identity comes from its observable behavior over time. So to prove you have produced a coalgebra, you must show:

1. what the states are
2. what can be observed from them
3. what evolves them
4. what the evolution law is
5. how behavioral equivalence or difference is tested
6. how the claim can fail
7. where it applies

If any one of those is missing, the coalgebra is not actually determined.

So this is a valid production test.

---

# Recursive use of the test

Now the part you asked for: how to use it recursively.

Suppose you have a **meta-system** that claims to mature an object-level coalgebra.

Then apply the same seven questions at both levels.

---

## Level 1: object coalgebra test

For example, STIG expert critic coalgebra.

Ask:

* What is the STIG critic state?
* What are its observable outputs?
* What inputs change it?
* What is its step map?
* What distinguishes two critic states?
* What falsifies the critic coalgebra?
* What STIG scope does it cover?

If yes, you have an object coalgebra.

---

## Level 2: meta-coalgebra test

Now test the system that matures that STIG coalgebra.

Ask:

* What is the state of the maturation machine?

  * candidate coalgebras
  * promoted coalgebras
  * criticism lineage
  * promotion/demotion status
* What are its observations?

  * coalgebra promotions, demotions, criticisms, fitness signals
* What events change it?

  * new trial, new break/fix result, new contradiction, new synthesis proposal
* What is its step map?
* What distinguishes two maturation states?
* What falsifies the maturation coalgebra?
* What scope does the maturation process cover?

If yes, then you have a coalgebra that matures a coalgebra.

---

# Recursive coalgebra theorem, practical form

Here is the recursive rule:

## Recursive Coalgebra Gate

A purported meta-coalgebra is valid only if:

1. it passes the Coalgebra Production Test itself, and
2. every object it promotes as a coalgebra also passes the Coalgebra Production Test at its own level.

This is the recursive test you wanted.

---

# Stronger anti-fake recursion rule

To prevent empty recursion, add this:

## No Recursive Promotion Without Lower-Level Coalgebra Validity

A meta-coalgebra may not promote, mature, or compare candidate object coalgebras unless those candidates already expose:

* state
* observation
* input/event
* step map
* distinction test
* falsifier
* scope

Otherwise the meta-level is pretending to mature something that has not yet been coherently specified.

That closes a major loophole.

---

# One-page version of the recursive test

For any candidate system `S`, ask:

1. **State Test**
   What is `X(S)`?

2. **Observation Test**
   What is `O(S)`?

3. **Event Test**
   What is `I(S)`?

4. **Behavior Test**
   What is `step_S : X(S) × I(S) → O(S) × X(S)` or equivalent?

5. **Distinction Test**
   How do we tell whether two states of `S` are behaviorally distinct?

6. **Falsifier Test**
   What would prove the proposed coalgebra for `S` is wrong?

7. **Scope Test**
   Under what declared scope does the coalgebra claim hold?

If all seven are answered, `S` qualifies as a coalgebra candidate.

Then for any meta-system `M` that claims to mature `S`, require:

* `M` passes the same seven tests
* `M` contains a rule that no `S` is promoted unless `S` also passes them

That is the recursive form.

---

# Example: STIG expert critic

## Object-level coalgebra

* `X`: witness trust state, survivor state, open criticisms, validator registry, scope coverage
* `O`: pullback judgments, criticisms, falsifiers, promotions/demotions
* `I`: new evidence, break, fix, new witness, trust-root change
* `step`: deterministic kernel + training update
* distinction: same input produces different judgments or criticism behavior
* falsifier: missed break, hidden failure, contradiction across versions
* scope: TMOS version, platform, topology

Passes if all explicit.

## Meta-level coalgebra

* `X_meta`: candidate critic coalgebras, promotion states, cross-domain history, thresholds, criticism lineages
* `O_meta`: promotion/demotion of critic coalgebras, comparative adequacy observations
* `I_meta`: new trial results, new domains, new break/fix campaigns
* `step_meta`: updates which critic coalgebras are provisional/promoted/demoted
* distinction: two meta-states differ if they produce different promotion/demotion behavior on same candidate
* falsifier: promotes a candidate that later fails its own coalgebra test
* scope: STIG domain family, witness family, training regime

---

# Example: robot learner

Same recursive pattern.

Object-level:

* robot planning/manipulation/tool-use coalgebra

Meta-level:

* coalgebra that matures robot object coalgebras through embodied criticism

So the same test works.

---

# Final proof-style statement

A system can be said to produce a coalgebra only if it determines a state space, observation space, event space, behavior map, behavioral distinction test, falsifier, and validity scope. This criterion is recursively reusable because any system that claims to mature or promote coalgebras must itself satisfy the same conditions, and must require them of the coalgebras it promotes. Therefore the seven-part Coalgebra Production Test is a valid recursive gate for proving not only that a design yields a coalgebra, but that higher-order designs genuinely yield coalgebras that mature other coalgebras rather than merely speaking about them.

---

# Short anchor

## Recursive Coalgebra Production Test

A system produces a coalgebra only if it explicitly defines:

* state
* observation
* event/input
* step/behavior map
* behavioral distinction test
* falsifier
* scope

Use the same test recursively:

* first on the object coalgebra
* then on the meta-coalgebra that matures it
* and forbid promotion unless both pass


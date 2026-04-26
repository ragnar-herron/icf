STATUS: EVIDENCE SOURCE
CANONICAL INTERPRETATION IN docs/canonical/CANONICAL_BACKLOG.md

---



## 1. Separate the three layers

Right now they are blurred:

* **Factory semantic maturity**

  * criteria DSL
  * lawful distinctions
  * adjudication logic
  * falsifiers
  * fixture corpus

* **Live adapter maturity**

  * real tmsh/rest capture
  * normalization into exact atomic measurables
  * representation coverage
  * replay against real captures

* **Export projection maturity**

  * honest rendering only
  * no invented truth
  * unresolved preserved
  * only promoted live adapters shown as live-capable

The correction is to make these layers impossible to confuse.

---

## 2. Add an explicit per-control capability model

Every control should carry at least these fields:

```text
semantic_maturity_status
live_adapter_status
export_projection_status
```

Recommended values:

```text
semantic_maturity_status:
  factory_validated
  under_criticism

live_adapter_status:
  not_started
  capture_only
  replay_verified
  live_verified
  promoted

export_projection_status:
  projected_unresolved
  advisory_only
  live_resolved
  blocked
```

Then the UI does not guess. It just renders this.

---

## 3. Change the UI contract immediately

Do this first.

### Controls with promoted live adapters

Show:

* Validate
* live pass/fail/open
* evidence/provenance
* post-fix revalidation path

### Controls without promoted live adapters

Show:

* `projected_unresolved`
* “Factory logic validated; live capture adapter pending promotion”
* link to factory fixture evidence
* no live validate button, or validate button scoped to “factory evidence only”

This fixes the overclaiming right away.

---

## 4. Stop treating recipes as adapters

A contract recipe is not a live adapter.

A contract tells you:

* what to observe
* where it should come from
* how it should be judged

A live adapter must additionally prove:

* it can capture the field on real devices
* it can normalize vendor/runtime variants
* it can preserve atomic pullback truth
* it survives replay and live checks

So make this a hard rule:

## No control may be marked live-capable until its observation bridge is promoted separately from its semantic contract.

---

## 5. Build an adapter promotion pipeline

For each control family:

### Step A — capture

Collect real tmsh/rest outputs from real F5 variants.

### Step B — normalize

Write deterministic extractors to produce the exact atomic measurable.

### Step C — replay

Run extracted values against:

* good fixture
* bad fixture
* representation variants
* malformed/noisy cases

### Step D — live verify

Run on actual appliances.

### Step E — promote

Only promote if:

* distinction-preserving gates pass
* factory/export equivalence passes
* replay fidelity is exact
* known-bad fails
* known-good survives

That is the observation bridge lifecycle.

---

## 6. Group controls into adapter families

Do not promote 67 one by one if you can avoid it.

Cluster by common observation shape, for example:

* scalar config values
* counts of attached profiles
* set membership / banned ports
* presence/absence of objects
* string/banner checks
* auth/policy settings

Then build one robust live adapter family at a time and map multiple controls onto it.

That is how you avoid drowning in bespoke work.

---

## 7. Add a mandatory gate before live truth

Before any control can emit live truth:

### Live Adapter Gate

* exact measurable identity proven
* atomic pullback proven
* representation variants covered
* known-bad fails
* known-good passes
* export matches factory
* scope declared
* unresolved honesty preserved

If this gate fails:

* no live truth
* only `projected_unresolved`

---

## 8. Add a coverage summary to the product

The product should always show something like:

```text
67 total controls
4 live-supported
63 factory-validated / live-adapter pending
0 silently inferred
```

That one summary will stop the user from thinking the bridge is complete when it is not.

---

## 9. Rename statuses so they stop misleading people

Use:

* `live_resolved`
* `projected_unresolved`
* `factory_validated_only`
* `advisory_only`
* `out_of_scope`

Avoid showing plain “unresolved” without context.

Because the current problem is not just truth, it is **truth communication**.

---

## 10. Do not rebuild the factory

Keep the factory stable.

The correction is mostly:

* adapter engineering
* capability labeling
* UI honesty
* promotion discipline

Do **not** respond by writing a second evaluator stack in Python or the web app.

---

## 11. Practical sequence

Do this in order:

1. Freeze factory semantics.
2. Add capability fields per control.
3. Change UI to distinguish factory-validated vs live-supported.
4. Disable or relabel live validation for non-promoted controls.
5. Build adapter-family promotion pipeline.
6. Promote one family at a time.
7. Recompute coverage after each promotion.

---

## 12. The shortest correction

**Make the system tell the truth about where truth comes from.**
The factory defines compliance truth.
The adapter earns observation truth.
The export may only project what those two have actually promoted.

That is how this is corrected.

If you follow that plan but don’t add enforcement, you’ll absolutely drift back into vibe coding. The fix is not more guidance—it’s **making vibe coding structurally impossible to ship**.

Here’s how you lock that in.

---

# 🔒 1. Make “vibe coding” a failing condition

Define it explicitly:

## Vibe coding (formal definition)

```text
Any code that produces or influences canonical truth
without being derived from:
- a contract
- a captured observation
- a validated normalization path
- a replayable test corpus
```

If any code meets that definition → **hard fail**.

---

# 🚫 2. Add a non-bypassable gate

## Adapter Legitimacy Gate (NEW — critical)

A control may emit live truth **only if**:

| Requirement               | Enforcement                         |
| ------------------------- | ----------------------------------- |
| Has contract DSL          | must exist in catalog               |
| Has capture evidence      | real tmsh/rest samples checked in   |
| Has normalization mapping | explicit field extraction mapping   |
| Has fixture coverage      | all 9 fixture classes               |
| Passes replay             | deterministic against captured data |
| Passes falsifiers         | known-bad must fail                 |
| Passes equivalence        | factory == export                   |
| Has promotion record      | signed/recorded promotion           |

If any missing:

```text
status = projected_unresolved
```

No exceptions.

---

# 🧱 3. Disallow hand-written evaluators at the boundary

Add a static rule:

## ❌ Forbidden in export / adapters

* per-control `evaluate_vXXXX()` functions
* inline comparison logic (`<=`, `>=`, etc.)
* parsing tmsh output directly in UI layer
* deriving verdicts outside the generic engine

## ✅ Only allowed

* generic interpreter
* declarative mapping
* contract-driven extraction

Enforce with:

* code review checklist
* lint rule (regex for `evaluate_v`)
* CI failure on detection

---

# 🧪 4. Require evidence-first development

No adapter starts with code.

Every adapter must start with:

```text
1. Real capture files
2. Expected atomic measurable values
3. Fixture classification
```

Only then can code exist.

If someone writes code before evidence exists:

→ **reject PR**

---

# 🔁 5. Force replay before live

No live adapter may run against real systems until:

```text
replay(captured_data) == expected_results
```

This prevents:

* guesswork parsing
* environment-dependent hacks
* invisible assumptions

---

# 🧬 6. Lock everything to the contract

Every adapter must be reducible to:

```text
(contract DSL)
→ (field binding)
→ (normalized measurable)
→ (generic predicate)
```

If any logic exists outside that chain:

→ **fail adapter legitimacy**

---

# 📦 7. Require a promotion artifact

No adapter is “done” until it produces:

```json
{
  "adapter_id": "...",
  "control_id": "...",
  "capture_refs": [...],
  "normalization_map": {...},
  "fixture_results": {...},
  "falsifier_results": {...},
  "replay_hash": "...",
  "promotion_signature": "...",
  "status": "promoted"
}
```

If that object doesn’t exist:

→ adapter is not real
→ export must not use it

---

# 🧯 8. Make the UI incapable of lying

The UI must not infer capability.

It must read:

```text
live_adapter_status
```

and render strictly:

| Status       | UI behavior               |
| ------------ | ------------------------- |
| promoted     | allow validate            |
| not promoted | show projected_unresolved |
| missing      | show not supported        |

No fallback logic allowed.

---

# 🧠 9. Force work into adapter families

Vibe coding thrives in one-off work.

Prevent it by requiring:

```text
every adapter must belong to a reusable family
```

Example families:

* scalar config
* list membership
* count-based
* presence/absence
* policy bindings

If a PR introduces a one-off adapter:

→ reject unless it generalizes

---

# 🧾 10. Add a “why is this correct?” requirement

Every adapter PR must answer:

```text
1. What exact measurable is extracted?
2. From which raw fields?
3. What are all known representations?
4. What fails?
5. What survives?
6. What is unresolved?
```

If the author can’t answer:

→ it’s vibe code

---

# 🧩 11. Make failures visible, not hidden

Vibe coding hides behind green UI.

Expose:

* unresolved count
* adapter coverage %
* falsifier failures
* representation gaps

Make the system uncomfortable when incomplete.

---

# 🔁 12. Add regression traps

Every bug becomes a permanent fixture.

Example:

* port `any/.0` parsing bug → fixture added forever

This makes future vibe shortcuts fail automatically.

---

# 🛑 13. Add a single kill rule

## 🔴 Ultimate anti-vibe rule

```text
No code path may produce a truth value
that cannot be reproduced from:
(contract + capture + normalization + generic evaluator)
```

If violated:

→ reject build
→ reject PR
→ block export

---

# 💡 What this does

This converts your system from:

```text
"please don't vibe code"
```

into:

```text
"vibe code cannot pass the gates"
```

---

# 🧭 Final anchor

**The factory already removed guesswork from truth.
These rules remove guesswork from observation.**

That’s how you prevent ending up right back where you started.

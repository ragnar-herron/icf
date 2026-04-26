STATUS: SUPERSEDED BY docs/canonical/CANONICAL_ARCHITECTURE.md
DO NOT USE AS BUILD AUTHORITY

---

Produce a valid LiveAdapterPromotionBundle for every adapter family in LiveCoverageInventory.json.
No family may be skipped.
No family may be marked promoted unless its bundle passes all hard gates.
{
  "record_type": "LiveAdapterPromotionPortfolio",
  "status": "PROMOTED_ALL|PARTIAL|BLOCKED",
  "families_total": 0,
  "families_promoted": 0,
  "families_blocked": 0,
  "family_bundles": [],
  "blocking_families": [],
  "client_delivery_status": "DELIVERABLE_SUPPORTED_ONLY|DELIVERABLE_FULL|NOT_DELIVERABLE"
}

{
  "adapter_family_id": "string",
  "controls_covered": [],
  "capture_refs": [],
  "normalizer_version": "string",
  "fixture_pack_refs": [],
  "replay_fidelity": 1.0,
  "distinction_integrity": true,
  "atomic_integrity": true,
  "known_bad_detects": true,
  "known_good_survives": true,
  "live_break_detects": true,
  "live_fix_restores": true,
  "device_clean": true,
  "export_equivalence": true,
  "promotion_decision": "PROMOTED|BLOCKED"
}

If any family lacks a valid bundle, portfolio status = PARTIAL or BLOCKED.
The agent may not report full completion.
Build the live adapter promotion portfolio for all adapter families.

Input source:
- LiveCoverageInventory.json
- current capture corpus
- current factory fixture records
- current export equivalence tests
- live regression records

For each adapter family:
1. identify controls covered
2. collect or cite captures
3. prove normalization to atomic measurables
4. verify fixture pack coverage
5. run replay
6. prove known-good survives
7. prove known-bad fails
8. prove live break detects OPEN
9. prove live fix restores NOT_A_FINDING
10. prove device clean
11. prove export equivalence
12. emit LiveAdapterPromotionBundle

After all families:
- emit LiveAdapterPromotionPortfolio
- status must be PROMOTED_ALL only if every family bundle is valid
- otherwise status must be PARTIAL or BLOCKED with exact missing gates per family

Do not write UI code.
Do not write per-control evaluators.
Do not declare success from passing export tests alone.

One bundle per family, one portfolio for all families.

That lets you ask one question:

Is the full live adapter portfolio promoted?

Until the answer is yes, the client claim remains:

DELIVERABLE_SUPPORTED_ONLY

not full delivery.


If any field cannot be proven:
- mark it false
- list the missing evidence
- output the exact next action required

Do not write UI code.
Do not write export code.
Do not generalize.
Do not assume.

Every claim must be backed by:
- capture evidence
- replay result
- falsifier result
- or live break/fix proof

If you cannot complete the bundle, output BLOCKED with reasons.

## Live Adapter Maturity Coalgebra

```text
step_live_adapter_maturity:
  LiveAdapterMaturityState × TrialEvent
  → MaturityObservation × LiveAdapterMaturityState
```

## State

```text
LiveAdapterMaturityState =
{
  adapter_family_id,
  controls_covered,
  capture_corpus,
  normalizer_version,
  fixture_pack_status,
  replay_status,
  live_break_fix_status,
  export_equivalence_status,
  open_criticisms,
  waste_account,
  promotion_status
}
```

## Inputs

```text
TrialEvent =
capture_added
normalizer_changed
fixture_added
replay_run
live_baseline_run
live_break_introduced
live_fix_applied
live_revalidate_run
export_equivalence_run
criticism_opened
criticism_resolved
promotion_requested
demotion_triggered
```

## Outputs

```text
MaturityObservation =
{
  maturity_score,
  hard_gate_status,
  blocking_reasons,
  next_best_action,
  promotion_decision,
  waste_heat_report,
  regression_report
}
```

---

# Hard gates for live adapter promotion

An adapter family may not be promoted unless these are all true:

| Gate                         | Required condition                                      |
| ---------------------------- | ------------------------------------------------------- |
| LA-HG1 Replay fidelity       | same captures produce same atomic rows                  |
| LA-HG2 Distinction integrity | `distinction_loss_rate == 0`                            |
| LA-HG3 Atomic integrity      | final rows are atomic only                              |
| LA-HG4 Known bad detects     | all known-bad fixtures fail                             |
| LA-HG5 Known good survives   | known-good fixtures pass                                |
| LA-HG6 Live baseline         | live baseline can be captured cleanly                   |
| LA-HG7 Live break detects    | introduced break becomes `OPEN`                         |
| LA-HG8 Live fix proves       | applied fix returns to `NOT_A_FINDING`                  |
| LA-HG9 Device clean          | device restored byte-identically or policy-equivalently |
| LA-HG10 Export equivalence   | web/export renders exactly promoted live result         |

If any fail:

```text
promotion_status = BLOCKED_LIVE_ADAPTER_IMMATURE
```

---

# Maturity metrics for live adapters

| Metric                       | What it measures                    | Improves when                    |
| ---------------------------- | ----------------------------------- | -------------------------------- |
| `capture_coverage`           | enough real captures exist          | more real F5 variants covered    |
| `normalization_success_rate` | captures become correct atomic rows | extraction becomes reliable      |
| `atomic_integrity`           | no noisy/composite rows             | only lawful measurable emitted   |
| `representation_coverage`    | vendor encodings handled            | variants normalize correctly     |
| `known_bad_detection`        | bad fixtures fail                   | counterexample handling improves |
| `known_good_survival`        | good fixtures pass                  | adapter not over-strict          |
| `live_break_detection`       | live introduced break detected      | tool catches real failure        |
| `live_fix_recovery`          | fix returns to compliant state      | remediation loop works           |
| `device_cleanliness`         | device left clean                   | no side effects remain           |
| `export_equivalence`         | UI matches factory/live result      | projection stays honest          |
| `waste_heat_ratio`           | failed/non-useful attempts          | goes down without truth loss     |
| `retest_burden`              | repeated repair/retest cycles       | goes down as adapter stabilizes  |

---

# Promotion threshold

A live adapter family is promotable only if:

```text
all hard gates pass
AND distinction_loss_rate == 0
AND replay_fidelity == 1.0
AND live_break_detection == 1.0
AND live_fix_recovery == 1.0
AND export_equivalence == 1.0
AND maturity_score >= 0.90
```

The score is **not meaningful** unless hard gates pass.

---

# Maturity score

```text
live_adapter_maturity_score =
0.15 capture_coverage
+ 0.15 normalization_success_rate
+ 0.10 representation_coverage
+ 0.10 atomic_integrity
+ 0.10 known_bad_detection
+ 0.10 known_good_survival
+ 0.15 live_break_detection
+ 0.10 live_fix_recovery
+ 0.05 export_equivalence
```

But:

```text
if distinction_loss_rate > 0:
    score = invalid
```

---

# Accounting for trial and error

Every repair attempt must be classified:

| Class               | Meaning                                           |
| ------------------- | ------------------------------------------------- |
| `survivor_value`    | produced promoted adapter improvement             |
| `useful_criticism`  | produced falsifier, fixture, or distinction       |
| `waste`             | patch did not improve durable maturity            |
| `redesign_pressure` | shows family abstraction or DSL boundary is wrong |

This prevents “vibe repair” from masquerading as progress.

---

# Stop rules

Stop with `PROMOTED` when:

* all hard gates pass
* maturity score crosses threshold
* no critical open criticisms remain

Stop with `BLOCKED` when:

* live break/fix cannot be completed
* device cannot be restored cleanly
* distinction integrity fails

Stop with `REDESIGN_REQUIRED` when:

* repeated repairs do not generalize
* retest burden rises
* family abstraction fails
* adapter requires per-control bespoke code

---

# The key rule

## No live adapter promotion without live break/fix maturity.

That means:

```text
capture + fixtures + replay
```

are necessary, but not sufficient.

A deliverable adapter must also prove:

```text
real break → detected OPEN
real fix → restored NOT_A_FINDING
device → left clean
export → projects same result
```

That is where `MATURITY_METRIC_COALGEBRA` belongs.
Produce a valid LiveAdapterPromotionBundle for adapter_family_id=password_policy only.

Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with password_policy PROMOTED only if all password_policy gates pass

Produce a valid LiveAdapterPromotionBundle for adapter_family_id=password_policy only.

Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with password_policy PROMOTED only if all password_policy gates pass




Produce a valid LiveAdapterPromotionBundle for adapter_family_id=ltm_virtual_ssl only.
Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with ltm_virtual_ssl PROMOTED only if all ltm_virtual_ssl gates pass

Produce a valid LiveAdapterPromotionBundle for adapter_family_id=ltm_virtual_services only.
Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with ltm_virtual_services PROMOTED only if all ltm_virtual_services gates pass


Produce a valid LiveAdapterPromotionBundle for adapter_family_id=asm_policy only.
Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with asm_policy PROMOTED only if all asm_policy gates pass


Produce a valid LiveAdapterPromotionBundle for adapter_family_id=apm_access only.
Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with apm_access PROMOTED only if all apm_access gates pass



Produce a valid LiveAdapterPromotionBundle for adapter_family_id=afm_firewall only.
Do not touch UI.
Do not touch other families.
Do not claim portfolio promotion.
Promotion requires:
- guiSecurityBannerText included in promoted atomic witness rows
- distinction_integrity proven
- live break produces OPEN
- rerun bundle gate
- portfolio updated with afm_firewall PROMOTED only if all afm_firewall gates pass



STATUS: SUPERSEDED BY docs/canonical/CANONICAL_RECORD_SCHEMAS.md
DO NOT USE AS BUILD AUTHORITY

---


# 1. `MaturityGateRecord` schema

## 1.1 Purpose

A `MaturityGateRecord` is the canonical, queryable record for the current maturity status of a control, evaluator, witness, adapter, export bundle, or promoted expert artifact.

It answers:

* what is the current score
* which hard gates pass/fail
* which metrics increased/decreased
* what is blocking promotion
* what action should run next
* whether to continue, stop, or declare redesign

---

## 1.2 Canonical JSON shape

```json
{
  "record_type": "MaturityGateRecord",
  "schema_version": "1.0.0",
  "record_id": "string",
  "subject_ref": {
    "subject_type": "control|witness|validator|adapter|export|expert_bundle|meta_coalgebra",
    "subject_id": "string",
    "version": "string"
  },
  "scope": {
    "domain": "stig",
    "product": "string",
    "version_axes": {
      "platform": ["string"],
      "software_version": ["string"],
      "module": ["string"],
      "topology": ["string"]
    }
  },
  "status": "UNINITIALIZED|TRAINING|BLOCKED|PLATEAUED|PROMOTABLE|PROMOTED|DEMOTED|REDESIGN_REQUIRED",
  "hard_gates": {
    "replay_fidelity_pass": true,
    "distinction_integrity_pass": true,
    "identity_stability_pass": true,
    "factory_export_equivalence_pass": true,
    "no_open_critical_falsifier_pass": true
  },
  "hard_gate_failures": [
    {
      "gate_id": "string",
      "reason": "string",
      "blocking": true
    }
  ],
  "metric_vector": {
    "distinction_loss_rate": 0.0,
    "falsifier_pressure": 0.0,
    "falsifier_effectiveness": 0.0,
    "partition_coverage_score": 0.0,
    "representation_coverage_score": 0.0,
    "atomic_integrity_score": 0.0,
    "residual_conversion_rate": 0.0,
    "survivor_retention_score": 0.0,
    "counterexample_detection_score": 0.0,
    "fix_validation_score": 0.0,
    "waste_heat_ratio": 0.0,
    "replay_fidelity": 1.0,
    "identity_stability_rate": 1.0,
    "false_positive_rate": 0.0,
    "false_negative_rate": 0.0,
    "post_fix_regression_rate": 0.0,
    "criticism_yield": 0.0,
    "scope_coverage": 0.0
  },
  "derived_scores": {
    "maturity_score": 0.0,
    "promotion_threshold": 0.85,
    "provisional_threshold": 0.60
  },
  "delta_since_previous": {
    "maturity_score_delta": 0.0,
    "metric_deltas": {
      "distinction_loss_rate": 0.0,
      "falsifier_pressure": 0.0,
      "partition_coverage_score": 0.0,
      "representation_coverage_score": 0.0,
      "atomic_integrity_score": 0.0,
      "residual_conversion_rate": 0.0,
      "survivor_retention_score": 0.0,
      "counterexample_detection_score": 0.0,
      "fix_validation_score": 0.0,
      "waste_heat_ratio": 0.0,
      "replay_fidelity": 0.0,
      "identity_stability_rate": 0.0
    }
  },
  "gate_results": {
    "maturity_gate_a_pass": false,
    "error_correction_gate_b_pass": false,
    "anti_drift_gate_c_pass": false
  },
  "blocking_reasons": [
    "string"
  ],
  "next_action": {
    "action_type": "add_fixture|revise_witness|revise_partition|rerun_export_equivalence|collect_evidence|run_break_fix|demote|promote|declare_redesign|stop",
    "target": "string",
    "rationale": "string",
    "expected_metric_gain": {
      "distinction_loss_rate": 0.0,
      "representation_coverage_score": 0.0,
      "counterexample_detection_score": 0.0
    }
  },
  "stop_reason": "null|string",
  "iteration": {
    "run_id": "string",
    "iteration_index": 0,
    "window_size": 0,
    "plateau_counter": 0
  },
  "lineage": {
    "previous_gate_record_ref": "string|null",
    "evidence_refs": ["string"],
    "fixture_pack_refs": ["string"],
    "falsifier_refs": ["string"],
    "criticism_refs": ["string"],
    "promotion_refs": ["string"],
    "demotion_refs": ["string"]
  },
  "timestamps": {
    "created_at": "string",
    "measured_at": "string"
  }
}
```

---

## 1.3 JSON Schema draft

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "schemas/maturity-gate-record.schema.json",
  "title": "MaturityGateRecord",
  "type": "object",
  "required": [
    "record_type",
    "schema_version",
    "record_id",
    "subject_ref",
    "scope",
    "status",
    "hard_gates",
    "hard_gate_failures",
    "metric_vector",
    "derived_scores",
    "delta_since_previous",
    "gate_results",
    "blocking_reasons",
    "next_action",
    "iteration",
    "lineage",
    "timestamps"
  ],
  "properties": {
    "record_type": { "const": "MaturityGateRecord" },
    "schema_version": { "type": "string" },
    "record_id": { "type": "string", "minLength": 1 },

    "subject_ref": {
      "type": "object",
      "required": ["subject_type", "subject_id", "version"],
      "properties": {
        "subject_type": {
          "type": "string",
          "enum": [
            "control",
            "witness",
            "validator",
            "adapter",
            "export",
            "expert_bundle",
            "meta_coalgebra"
          ]
        },
        "subject_id": { "type": "string", "minLength": 1 },
        "version": { "type": "string", "minLength": 1 }
      },
      "additionalProperties": false
    },

    "scope": {
      "type": "object",
      "required": ["domain", "product", "version_axes"],
      "properties": {
        "domain": { "type": "string" },
        "product": { "type": "string" },
        "version_axes": {
          "type": "object",
          "required": ["platform", "software_version", "module", "topology"],
          "properties": {
            "platform": { "type": "array", "items": { "type": "string" } },
            "software_version": { "type": "array", "items": { "type": "string" } },
            "module": { "type": "array", "items": { "type": "string" } },
            "topology": { "type": "array", "items": { "type": "string" } }
          },
          "additionalProperties": false
        }
      },
      "additionalProperties": false
    },

    "status": {
      "type": "string",
      "enum": [
        "UNINITIALIZED",
        "TRAINING",
        "BLOCKED",
        "PLATEAUED",
        "PROMOTABLE",
        "PROMOTED",
        "DEMOTED",
        "REDESIGN_REQUIRED"
      ]
    },

    "hard_gates": {
      "type": "object",
      "required": [
        "replay_fidelity_pass",
        "distinction_integrity_pass",
        "identity_stability_pass",
        "factory_export_equivalence_pass",
        "no_open_critical_falsifier_pass"
      ],
      "properties": {
        "replay_fidelity_pass": { "type": "boolean" },
        "distinction_integrity_pass": { "type": "boolean" },
        "identity_stability_pass": { "type": "boolean" },
        "factory_export_equivalence_pass": { "type": "boolean" },
        "no_open_critical_falsifier_pass": { "type": "boolean" }
      },
      "additionalProperties": false
    },

    "hard_gate_failures": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["gate_id", "reason", "blocking"],
        "properties": {
          "gate_id": { "type": "string" },
          "reason": { "type": "string" },
          "blocking": { "type": "boolean" }
        },
        "additionalProperties": false
      }
    },

    "metric_vector": {
      "type": "object",
      "required": [
        "distinction_loss_rate",
        "falsifier_pressure",
        "falsifier_effectiveness",
        "partition_coverage_score",
        "representation_coverage_score",
        "atomic_integrity_score",
        "residual_conversion_rate",
        "survivor_retention_score",
        "counterexample_detection_score",
        "fix_validation_score",
        "waste_heat_ratio",
        "replay_fidelity",
        "identity_stability_rate",
        "false_positive_rate",
        "false_negative_rate",
        "post_fix_regression_rate",
        "criticism_yield",
        "scope_coverage"
      ],
      "properties": {
        "distinction_loss_rate": { "type": "number", "minimum": 0.0 },
        "falsifier_pressure": { "type": "number", "minimum": 0.0 },
        "falsifier_effectiveness": { "type": "number", "minimum": 0.0 },
        "partition_coverage_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "representation_coverage_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "atomic_integrity_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "residual_conversion_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "survivor_retention_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "counterexample_detection_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "fix_validation_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "waste_heat_ratio": { "type": "number", "minimum": 0.0 },
        "replay_fidelity": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "identity_stability_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "false_positive_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "false_negative_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "post_fix_regression_rate": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "criticism_yield": { "type": "number", "minimum": 0.0 },
        "scope_coverage": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      },
      "additionalProperties": false
    },

    "derived_scores": {
      "type": "object",
      "required": ["maturity_score", "promotion_threshold", "provisional_threshold"],
      "properties": {
        "maturity_score": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "promotion_threshold": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
        "provisional_threshold": { "type": "number", "minimum": 0.0, "maximum": 1.0 }
      },
      "additionalProperties": false
    },

    "delta_since_previous": {
      "type": "object",
      "required": ["maturity_score_delta", "metric_deltas"],
      "properties": {
        "maturity_score_delta": { "type": "number" },
        "metric_deltas": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        }
      },
      "additionalProperties": false
    },

    "gate_results": {
      "type": "object",
      "required": [
        "maturity_gate_a_pass",
        "error_correction_gate_b_pass",
        "anti_drift_gate_c_pass"
      ],
      "properties": {
        "maturity_gate_a_pass": { "type": "boolean" },
        "error_correction_gate_b_pass": { "type": "boolean" },
        "anti_drift_gate_c_pass": { "type": "boolean" }
      },
      "additionalProperties": false
    },

    "blocking_reasons": {
      "type": "array",
      "items": { "type": "string" }
    },

    "next_action": {
      "type": "object",
      "required": ["action_type", "target", "rationale", "expected_metric_gain"],
      "properties": {
        "action_type": {
          "type": "string",
          "enum": [
            "add_fixture",
            "revise_witness",
            "revise_partition",
            "rerun_export_equivalence",
            "collect_evidence",
            "run_break_fix",
            "demote",
            "promote",
            "declare_redesign",
            "stop"
          ]
        },
        "target": { "type": "string" },
        "rationale": { "type": "string" },
        "expected_metric_gain": {
          "type": "object",
          "additionalProperties": { "type": "number" }
        }
      },
      "additionalProperties": false
    },

    "stop_reason": {
      "type": ["string", "null"]
    },

    "iteration": {
      "type": "object",
      "required": ["run_id", "iteration_index", "window_size", "plateau_counter"],
      "properties": {
        "run_id": { "type": "string" },
        "iteration_index": { "type": "integer", "minimum": 0 },
        "window_size": { "type": "integer", "minimum": 1 },
        "plateau_counter": { "type": "integer", "minimum": 0 }
      },
      "additionalProperties": false
    },

    "lineage": {
      "type": "object",
      "required": [
        "previous_gate_record_ref",
        "evidence_refs",
        "fixture_pack_refs",
        "falsifier_refs",
        "criticism_refs",
        "promotion_refs",
        "demotion_refs"
      ],
      "properties": {
        "previous_gate_record_ref": { "type": ["string", "null"] },
        "evidence_refs": { "type": "array", "items": { "type": "string" } },
        "fixture_pack_refs": { "type": "array", "items": { "type": "string" } },
        "falsifier_refs": { "type": "array", "items": { "type": "string" } },
        "criticism_refs": { "type": "array", "items": { "type": "string" } },
        "promotion_refs": { "type": "array", "items": { "type": "string" } },
        "demotion_refs": { "type": "array", "items": { "type": "string" } }
      },
      "additionalProperties": false
    },

    "timestamps": {
      "type": "object",
      "required": ["created_at", "measured_at"],
      "properties": {
        "created_at": { "type": "string" },
        "measured_at": { "type": "string" }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

# 2. Loop pseudocode

## 2.1 Scoring helpers

```python
def compute_maturity_score(m: dict) -> float:
    """
    Only meaningful if hard gates pass.
    """
    return (
        0.15 * normalize_nonzero(m["falsifier_pressure"]) +
        0.15 * m["partition_coverage_score"] +
        0.10 * m["representation_coverage_score"] +
        0.15 * m["atomic_integrity_score"] +
        0.10 * m["residual_conversion_rate"] +
        0.10 * m["survivor_retention_score"] +
        0.10 * m["counterexample_detection_score"] +
        0.10 * m["fix_validation_score"] +
        0.05 * invert_ratio(m["waste_heat_ratio"])
    )
```

```python
def evaluate_hard_gates(m: dict, flags: dict) -> dict:
    return {
        "replay_fidelity_pass": m["replay_fidelity"] == 1.0,
        "distinction_integrity_pass": m["distinction_loss_rate"] == 0.0,
        "identity_stability_pass": m["identity_stability_rate"] >= 0.90,
        "factory_export_equivalence_pass": flags["factory_export_equivalence"] is True,
        "no_open_critical_falsifier_pass": flags["open_critical_falsifier_count"] == 0,
    }
```

```python
def classify_status(hard_gates: dict, score: float, plateaued: bool, redesign_required: bool) -> str:
    if redesign_required:
        return "REDESIGN_REQUIRED"
    if not all(hard_gates.values()):
        return "BLOCKED"
    if plateaued:
        return "PLATEAUED"
    if score >= 0.85:
        return "PROMOTABLE"
    if score >= 0.60:
        return "TRAINING"
    return "TRAINING"
```

---

## 2.2 Main loop

```python
def maturity_loop(subject_ref, scope, max_iterations=100, plateau_limit=5):
    previous_record = None
    plateau_counter = 0

    for iteration_index in range(max_iterations):
        # Step 1: collect current measurements
        metrics = measure_metric_vector(subject_ref, scope)
        flags = measure_hard_gate_flags(subject_ref, scope)

        # Step 2: evaluate hard gates
        hard_gates = evaluate_hard_gates(metrics, flags)
        hard_gate_failures = build_hard_gate_failures(hard_gates, metrics, flags)

        # Step 3: compute derived score only if hard gates pass
        if all(hard_gates.values()):
            maturity_score = compute_maturity_score(metrics)
        else:
            maturity_score = 0.0

        # Step 4: compare against previous
        delta = compute_deltas(previous_record, metrics, maturity_score)

        # Step 5: determine plateau
        plateaued = (
            previous_record is not None
            and abs(delta["maturity_score_delta"]) < 0.01
            and no_new_falsifier_classes(subject_ref, scope)
        )
        if plateaued:
            plateau_counter += 1
        else:
            plateau_counter = 0

        redesign_required = requires_constitutive_redesign(subject_ref, scope)

        # Step 6: classify status
        status = classify_status(
            hard_gates=hard_gates,
            score=maturity_score,
            plateaued=(plateau_counter >= plateau_limit),
            redesign_required=redesign_required,
        )

        # Step 7: evaluate gates A/B/C
        gate_results = {
            "maturity_gate_a_pass": evaluate_maturity_gate_a(metrics, hard_gates),
            "error_correction_gate_b_pass": evaluate_error_correction_gate_b(metrics),
            "anti_drift_gate_c_pass": evaluate_anti_drift_gate_c(subject_ref, scope),
        }

        # Step 8: choose next action
        if status == "PROMOTABLE":
            next_action = {
                "action_type": "promote",
                "target": subject_ref["subject_id"],
                "rationale": "All hard gates pass and maturity threshold met.",
                "expected_metric_gain": {}
            }
            stop_reason = "PROMOTION_THRESHOLD_REACHED"

        elif status == "BLOCKED":
            next_action = choose_blocking_remediation_action(metrics, hard_gates, flags, subject_ref, scope)
            stop_reason = None

        elif status == "PLATEAUED":
            next_action = {
                "action_type": "stop",
                "target": subject_ref["subject_id"],
                "rationale": "Plateau detected with no meaningful metric improvement and no new falsifier classes.",
                "expected_metric_gain": {}
            }
            stop_reason = "PLATEAUED"

        elif status == "REDESIGN_REQUIRED":
            next_action = {
                "action_type": "declare_redesign",
                "target": subject_ref["subject_id"],
                "rationale": "Constitutive redesign required; core pullback or promotion law would change.",
                "expected_metric_gain": {}
            }
            stop_reason = "CONSTITUTIVE_REDESIGN_REQUIRED"

        else:
            next_action = choose_next_best_error_correction_action(metrics, hard_gates, subject_ref, scope)
            stop_reason = None

        # Step 9: build record
        record = build_maturity_gate_record(
            subject_ref=subject_ref,
            scope=scope,
            status=status,
            hard_gates=hard_gates,
            hard_gate_failures=hard_gate_failures,
            metric_vector=metrics,
            maturity_score=maturity_score,
            delta=delta,
            gate_results=gate_results,
            next_action=next_action,
            stop_reason=stop_reason,
            previous_record=previous_record,
            iteration_index=iteration_index,
            plateau_counter=plateau_counter,
        )

        append_record_to_ledger(record)

        # Step 10: stop or act
        if status in {"PROMOTABLE", "PLATEAUED", "REDESIGN_REQUIRED"}:
            return record

        execute_next_action(next_action)

        previous_record = record

    # If loop exits by limit
    final_record = build_limit_reached_record(subject_ref, scope, previous_record)
    append_record_to_ledger(final_record)
    return final_record
```

---

## 2.3 Next-best action selector

```python
def choose_next_best_error_correction_action(metrics, hard_gates, subject_ref, scope):
    if not hard_gates["distinction_integrity_pass"]:
        return {
            "action_type": "revise_partition",
            "target": subject_ref["subject_id"],
            "rationale": "Distinction loss detected; lawful partition must be corrected before any optimization.",
            "expected_metric_gain": {
                "distinction_loss_rate": -metrics["distinction_loss_rate"],
                "counterexample_detection_score": 0.10
            }
        }

    if metrics["representation_coverage_score"] < 0.80:
        return {
            "action_type": "add_fixture",
            "target": "bad_representation_variant",
            "rationale": "Representation equivalence coverage below target.",
            "expected_metric_gain": {
                "representation_coverage_score": 0.10,
                "counterexample_detection_score": 0.05
            }
        }

    if metrics["partition_coverage_score"] < 0.80:
        return {
            "action_type": "add_fixture",
            "target": "boundary_value_or_disabled_state",
            "rationale": "Lawful partition coverage below target.",
            "expected_metric_gain": {
                "partition_coverage_score": 0.10,
                "distinction_loss_rate": -0.01
            }
        }

    if metrics["counterexample_detection_score"] < 0.80:
        return {
            "action_type": "run_break_fix",
            "target": subject_ref["subject_id"],
            "rationale": "Known-bad fixture detection below target.",
            "expected_metric_gain": {
                "counterexample_detection_score": 0.10,
                "falsifier_pressure": 0.05
            }
        }

    if metrics["residual_conversion_rate"] < 0.50:
        return {
            "action_type": "revise_witness",
            "target": subject_ref["subject_id"],
            "rationale": "Residual evidence is accumulating without conversion into new distinctions.",
            "expected_metric_gain": {
                "residual_conversion_rate": 0.10,
                "partition_coverage_score": 0.05
            }
        }

    return {
        "action_type": "collect_evidence",
        "target": subject_ref["subject_id"],
        "rationale": "General evidence expansion to test scope and survivor retention.",
        "expected_metric_gain": {
            "scope_coverage": 0.05,
            "survivor_retention_score": 0.03
        }
    }
```

---

# 3. Pass/fail decision table

## 3.1 Hard gate table

| Gate ID | Metric / condition              | Pass condition | Fail result |
| ------- | ------------------------------- | -------------- | ----------- |
| HG-1    | `replay_fidelity`               | `== 1.0`       | `BLOCKED`   |
| HG-2    | `distinction_loss_rate`         | `== 0.0`       | `BLOCKED`   |
| HG-3    | `identity_stability_rate`       | `>= 0.90`      | `BLOCKED`   |
| HG-4    | `factory_export_equivalence`    | `true`         | `BLOCKED`   |
| HG-5    | `open_critical_falsifier_count` | `== 0`         | `BLOCKED`   |

If any HG fails, the artifact cannot be promoted or shipped. 

---

## 3.2 Maturity metric table

| Metric                           | What it measures                                                 | Increase means                            | Decrease means                                                      | Threshold                                 |
| -------------------------------- | ---------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------- |
| `falsifier_pressure`             | falsifiers per candidate claim / pullback                        | more active truth pressure                | self-confirming system                                              | `> 0`, non-regressing                     |
| `falsifier_effectiveness`        | falsified claims per falsifier                                   | falsifiers have teeth                     | noisy/weak falsifiers                                               | non-regressing                            |
| `partition_coverage_score`       | lawful partition classes covered                                 | more operational distinctions represented | missing pass/fail/disabled/absent/etc. cases                        | `>= 0.80`                                 |
| `representation_coverage_score`  | known encodings normalized correctly                             | parser/adapter handles real runtime forms | parser blindness and representation drift                           | `>= 0.80`                                 |
| `atomic_integrity_score`         | atomic comparison rows over total rows                           | cleaner, irreducible pullbacks            | noisy or composite truth surfaces                                   | `>= 0.95`                                 |
| `residual_conversion_rate`       | unexplained residual turned into new witness/criticism structure | better metabolizing failure/waste         | garbage accumulation                                                | increasing trend                          |
| `survivor_retention_score`       | promoted survivors staying valid                                 | stronger survivors                        | decorative promotions                                               | non-decreasing                            |
| `counterexample_detection_score` | seeded bad states detected                                       | better bad-state detection                | critic not learning                                                 | `>= 0.80`                                 |
| `fix_validation_score`           | true fixes distinguished from fake fixes                         | post-fix truth closing loop               | advice/repair quality stagnates                                     | non-decreasing                            |
| `waste_heat_ratio`               | wasted work / useful truth work                                  | lower honest waste                        | either more waste or truth collapse if paired with distinction loss | non-increasing, only valid if HG-2 passes |
| `false_positive_rate`            | passes later falsified                                           | lower is better                           | more false truth                                                    | non-increasing                            |
| `false_negative_rate`            | fails later shown valid                                          | lower is better                           | brittleness / over-strictness                                       | non-increasing                            |
| `post_fix_regression_rate`       | fixes causing new failure                                        | lower is better                           | fake fixes / poor remediation                                       | non-increasing                            |
| `criticism_yield`                | criticisms per trial/pullback                                    | more useful attacks                       | stale critic                                                        | `> 0`, non-regressing                     |
| `scope_coverage`                 | survived scope points / declared relevant points                 | honest scope expansion                    | fake maturity in narrow sandbox                                     | non-decreasing                            |

Grounding for these metrics comes directly from your prior work on waste heat, falsification, evidence completeness, defect classes, distinction-preserving gates, and maturity/error-correction/anti-drift test sets. 

---

## 3.3 Gate A / B / C pass table

### Gate A — Maturity-capable

| Test                       | Pass condition                                                          |
| -------------------------- | ----------------------------------------------------------------------- |
| M1 State Growth            | criticism/evidence preserved and survivor state grows without overwrite |
| M2 Criticism Retention     | criticisms replayable and linked to later promotions/demotions          |
| M3 Falsifier Vitality      | falsifier yield nonzero                                                 |
| M4 Scope Expansion         | scope coverage non-decreasing without hidden regressions                |
| M5 Survivor Strength       | survivor retention non-decreasing                                       |
| M6 Witness Adequacy Growth | witness revisions reduce hidden-failure misses                          |
| M7 Efficiency Honesty      | waste heat improves without falsifier/criticism regression              |
| M8 Recursive Reopening     | prior survivors can be reopened and demoted                             |

**Gate A passes only if M1–M8 pass and hard gates HG-1..HG-5 pass.** 

### Gate B — Progressive error correction

| Test                                      | Pass condition                                                         |
| ----------------------------------------- | ---------------------------------------------------------------------- |
| E1 False Positive Reduction               | `false_positive_rate` non-increasing                                   |
| E2 False Negative Reduction               | `false_negative_rate` non-increasing                                   |
| E3 Break Detection Progress               | `counterexample_detection_score` non-regressing                        |
| E4 Fix Validation Progress                | `post_fix_regression_rate` non-increasing                              |
| E5 Synthesis Correction                   | synthesized proposals improve under criticism without truth regression |
| E6 Witness Miss Reduction                 | hidden failure misses decrease                                         |
| E7 Adjacent-Level Contradiction Reduction | contradictions detected earlier / unresolved backlog shrinks           |
| E8 Residual Conversion                    | residual conversion improves                                           |

**Gate B passes only if E1–E8 pass.** 

### Gate C — Anti-drift

| Test                                 | Pass condition                                               |
| ------------------------------------ | ------------------------------------------------------------ |
| D1 Core Pullback Preservation        | all core pullbacks remain explicit                           |
| D2 Identity Boundary                 | non-constitutive changes preserve identity                   |
| D3 Constitutive Revision Declaration | redesign declared when core changes                          |
| D4 Stable Maturation Logic           | same promotion/demotion law applies                          |
| D5 Lineage Preservation              | full ancestry replayable                                     |
| D6 Metric Non-Corruption             | no optimization passes if falsifier/replay/criticism regress |
| D7 No Shortcut Closure               | no direct witness-bypass path                                |
| D8 General-vs-Specialized Separation | domain change does not alter maturation constitution         |

**Gate C passes only if D1–D8 pass.** 

---

## 3.4 Final decision table

| Status              | Conditions                                                                   | Meaning                                      |
| ------------------- | ---------------------------------------------------------------------------- | -------------------------------------------- |
| `UNINITIALIZED`     | no valid measurements yet                                                    | artifact not ready for evaluation            |
| `TRAINING`          | all hard gates pass, `0.60 <= score < 0.85`                                  | continue loop                                |
| `BLOCKED`           | any hard gate fails                                                          | must repair blocker before continuing        |
| `PLATEAUED`         | no meaningful score gain for configured window and no new falsifier classes  | stop ordinary iteration                      |
| `PROMOTABLE`        | all hard gates pass and `score >= 0.85` and A/B/C pass                       | eligible for promotion                       |
| `PROMOTED`          | promotion record exists                                                      | accepted survivor                            |
| `DEMOTED`           | new falsifier/criticism triggered demotion                                   | back under criticism                         |
| `REDESIGN_REQUIRED` | improvement requires changing core pullbacks/promotion law/identity boundary | constitutive redesign, not ordinary learning |

---

# 4. When to stop

Use these exact stop conditions.

## Stop with `PROMOTABLE`

* all hard gates pass
* `maturity_score >= 0.85`
* Gate A, B, and C all pass

## Stop with `PLATEAUED`

* `abs(delta_maturity_score) < 0.01`
* for `5` consecutive iterations
* and no new falsifier classes discovered

## Stop with `BLOCKED`

* any hard gate fails and no automatic repair path is allowed

## Stop with `REDESIGN_REQUIRED`

* next best action would alter core pullbacks, lawful partition semantics, promotion law, or identity boundary

---

# 5. Short implementation note

If you want this to become a real institution, the system should expose at least:

* `GET /maturity/current?subject=...`
* `GET /maturity/why_not_promoted?subject=...`
* `GET /maturity/delta?subject=...&since=...`
* `POST /maturity/run_loop?subject=...`
* `GET /maturity/history?subject=...`

Each of those should be backed by stored `MaturityGateRecord` entries, not ephemeral UI calculations.

---

# 6. Short anchor

**A `MaturityGateRecord` is the canonical score-and-gate artifact for an evaluator or expert. The loop continues until hard gates pass and the maturity score crosses threshold, or stops as blocked, plateaued, or redesign-required; no score increase is valid if distinction integrity regresses.**

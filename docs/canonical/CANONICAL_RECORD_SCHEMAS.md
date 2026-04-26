# Canonical Record Schemas

## Status

STATUS: CANONICAL RECORD-SCHEMA AUTHORITY

All records must be JSON-serializable unless a producer explicitly declares another format. Each record must include `record_kind`, `generated_at`, `producer`, `inputs`, and `status` unless noted otherwise.

## DistinctionCatalogRecord

Purpose: captures STIG catalog semantics and source traceability.

Producer: Phase 2 catalog builder.

Consumer: maturity gates, adapter promotion, export projection.

Required fields:

- `record_kind`
- `catalog_version`
- `control_count`
- `source_inputs`
- `controls`
- `traceability`

Validation rules:

- every control has a `vuln_id`
- every control links to source STIG and assertion contract data

Example path: `factory_exports/stig_expert_critic/data/ControlCatalog.json`

## MeasurableBindingRecord

Purpose: binds each contract measurable to admissible runtime or external evidence.

Producer: Phase 2 catalog builder or Phase 3 adapter promoter.

Consumer: adapter fixtures, live evaluators, export projection.

Required fields:

- `vuln_id`
- `measurable`
- `evidence_source`
- `runtime_path`
- `source_type`
- `admissibility`

Validation rules:

- one measurable maps to one lawful runtime/external evidence role
- blocked external fields cannot be treated as appliance fields

Example path: `bridge/ExportBundle.json` pullback rows; `FactoryDistinctionBundle.json`

## LawfulPartitionRecord

Purpose: defines pass/open/unresolved partitions for a control.

Producer: Phase 2 contract semantics.

Consumer: evaluator, maturity gates, export.

Required fields:

- `vuln_id`
- `not_a_finding_partition`
- `open_partition`
- `unresolved_partition`
- `external_evidence_conditions`

Validation rules:

- partitions are mutually distinguishable
- unresolved is not collapsed into pass/open

Example path: `docs/assertion_contracts.json`

## AtomicPullbackRowRecord

Purpose: stores one row of required-vs-observed comparison for a promoted control.

Producer: evaluator or bridge promotion pipeline.

Consumer: export projection, adjudication tab, audit reports.

Required fields:

- `vuln_id`
- `fields`
- `required`
- `observed`
- `operator_summary`
- `verdict`

Validation rules:

- each field in `fields` exists in both `required` and `observed`
- verdict is `pass`, `fail`, or `unresolved`

Example path: `bridge/ExportBundle.json.entries[].pullback_row`

## FixtureExpectationRecord

Purpose: proves adapter behavior across mandatory fixture classes.

Producer: Phase 3 fixture runner.

Consumer: promotion portfolio, maturity gate.

Required fields:

- `fixture_class`
- `evidence`
- `expected_verdict`
- `actual_verdict`
- `passed`

Validation rules:

- each promoted control has all required fixture classes
- bad, malformed, disabled, absent, and out-of-scope fixtures cannot produce false pass

Example path: `bridge/LegitimacyRecords.json.records[].fixture_results[]`

## LiveAdapterPromotionBundle

Purpose: promotes or blocks one adapter family.

Producer: Phase 3 adapter promotion.

Consumer: portfolio, live regression, delivery gate.

Required fields:

- `family`
- `controls`
- `promoted_controls`
- `blocked_controls`
- `fixture_summary`
- `dp_gate_summary`
- `status`

Validation rules:

- `status == PROMOTED` only when all included controls pass required promotion gates
- blocked controls carry explicit reason

Example path: `factory_exports/stig_expert_critic/data/LiveAdapterPromotionBundle.*.json`

## LiveAdapterPromotionPortfolio

Purpose: aggregate all family promotion bundles.

Producer: Phase 3 adapter promotion.

Consumer: break/fix regression, export projection, client deliverability.

Required fields:

- `record_kind`
- `families`
- `promoted_control_count`
- `unresolved_control_count`
- `status`

Validation rules:

- counts reconcile to the STIG control inventory
- unsupported controls are not listed as live-supported

Example path: `factory_exports/stig_expert_critic/data/LiveAdapterPromotionPortfolio.json`

## LiveRegressionEvidenceBundle

Purpose: captures live break/fix campaign evidence and dispositions.

Producer: Phase 4 live campaign.

Consumer: delivery profile, backlog, release gate.

Required fields:

- `host`
- `campaign_id`
- `control_results`
- `evidence_refs`
- `external_evidence_refs`
- `open_findings`
- `blocked_external`

Validation rules:

- every live finding has a source evidence ref
- real failures remain open until fixed and rerun

Example path: `docs/LIVE_RUN_REPORT.md`; generated live campaign ledgers

## ExternalEvidencePackage

Purpose: contains organization-provided evidence that cannot be collected from appliance runtime alone.

Producer: operator or external evidence capture.

Consumer: live regression, adapter promotion, delivery profile.

Required fields:

- `package_id`
- `vuln_ids`
- `evidence_type`
- `provider`
- `evidence`
- `attestation`
- `validity_window`

Validation rules:

- package must identify responsible provider and validity window
- package cannot be silently synthesized by the UI

Example path: `factory_exports/stig_expert_critic/data/ExternalEvidencePackage.*.json`

## BackupCombinedMeasurable

Purpose: combines appliance backup observations with external backup policy evidence.

Producer: backup evidence tools.

Consumer: backup family evaluator and client delivery gate.

Required fields:

- `backup_archives`
- `external_policy`
- `combined_status`
- `evidence_refs`

Validation rules:

- local archive evidence alone cannot prove organizational backup schedule

Example path: `factory_exports/stig_expert_critic/data/BackupCombinedMeasurable.json`

## ExportProjectionGateRecord

Purpose: proves export/web_app is a governed projection.

Producer: Phase 5 export verification.

Consumer: client deliverability and release gates.

Required fields:

- `projection_equivalence_rate`
- `unresolved_preservation_rate`
- `frontend_truth_invention_incidents`
- `role_drift_incidents`
- `ep_gates`
- `status`

Validation rules:

- EP gates all pass
- no unresolved entry renders as resolved

Example path: output from `python -m bridge.verify_ep_gates`

## ClientDeliverabilityGateRecord

Purpose: proves client bundle claim is supportable.

Producer: Phase 6 delivery verification.

Consumer: release gate.

Required fields:

- `client_status`
- `supported_controls`
- `supported_families`
- `blocked_external`
- `open_findings`
- `declared_boundaries`
- `status`

Validation rules:

- client status cannot claim full live support unless every required gate passes

Example path: `factory_exports/stig_expert_critic/data/ClientDeliverabilityGateRecord.json`

## MaturityGateRecord

Purpose: captures maturity hard gates and metric vector.

Producer: maturity evaluation commands.

Consumer: release gate and architecture review.

Required fields:

- `hard_gates`
- `metric_vector`
- `production_gaps`
- `status`

Validation rules:

- hard gate failure blocks promotion regardless of aggregate score

Example path: maturity command output or `docs/info_maturity_score.md`

## WasteAccountingRecord

Purpose: quantifies unresolved, blocked, unsupported, or redesign-required scope.

Producer: maturity/delivery gate.

Consumer: delivery profile and backlog.

Required fields:

- `total_controls`
- `promoted_controls`
- `projected_unresolved`
- `blocked_external`
- `open_findings`
- `waste_heat_ratio`

Validation rules:

- unresolved scope must be counted, not hidden
- delivery claims must cite waste accounting

Example path: shipping gate output

## RedesignDecisionRecord

Purpose: records when a requirement cannot be lawfully represented by the current architecture.

Producer: any blocking gate.

Consumer: canonical backlog and release gate.

Required fields:

- `decision_id`
- `affected_controls`
- `reason`
- `failed_gate`
- `required_redesign`
- `status`

Validation rules:

- redesign-required items cannot remain as generic backlog forever

Example path: future `docs/canonical/CANONICAL_BACKLOG.md` entries

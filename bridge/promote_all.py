"""
bridge/promote_all.py

End-to-end orchestration of the adapter promotion pipeline.

1. Load assertion contracts, distinction bundle, outcome matrix, manifest
2. For each adapter family (sorted by control count descending):
   a. Extract evidence for all member controls
   b. Evaluate all member controls
   c. Run fixture packs for all member controls
   d. Emit legitimacy records
3. Bundle results for export
4. Print shipping gate summary
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from bridge.evidence_extractor import (
    extract_evidence_for_control_with_derivation,
    load_manifest,
    load_outcome_matrix,
)
from bridge.family_evaluator import (
    load_contracts,
    load_distinction_bundle,
    evaluate_control,
)
from bridge.fixture_runner import run_fixture_suite, AdapterLegitimacyRecord
from bridge.export_bundler import (
    build_export_bundle,
    write_export_bundle,
    print_shipping_gate,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def classify_families(contracts: list[dict]) -> dict[str, list[dict]]:
    """Classify contracts into adapter families by criteria pattern shape."""
    families: dict[str, list[dict]] = defaultdict(list)
    for c in contracts:
        naf = c["criteria"]["not_a_finding"]
        fields = c["evidence_required"]

        if len(fields) == 1:
            if "==" in naf and ("true" in naf or "false" in naf or "enabled" in naf):
                families["boolean_flag"].append(c)
            elif ">=" in naf or "<=" in naf:
                families["scalar_threshold"].append(c)
            elif "==" in naf:
                val_part = naf.split("==")[1].strip().split()[0].strip("'\"")
                try:
                    int(val_part)
                    families["integer_equality"].append(c)
                except ValueError:
                    families["string_match"].append(c)
            else:
                families["boolean_flag"].append(c)
        elif " AND " in naf or " OR " in naf:
            families["compound_boolean"].append(c)
        else:
            families["boolean_flag"].append(c)

    return dict(families)


def run_pipeline() -> None:
    start = time.time()

    print("=" * 60)
    print("  ICF ADAPTER PROMOTION PIPELINE")
    print("  INVARIANT: Projection may not exist unless")
    print("             Adapter coalgebra is promoted.")
    print("=" * 60)

    print("\n[1/4] Loading domain data...")
    manifest = load_manifest()
    matrix = load_outcome_matrix()
    contracts = load_contracts()
    bundle = load_distinction_bundle()
    print(f"  Contracts: {len(contracts)}")
    print(f"  Bindings:  {len(bundle)}")
    print(f"  Snapshots: {len(manifest['snapshots'])}")

    print("\n[2/4] Classifying adapter families...")
    families = classify_families(contracts)
    for fam_name, members in sorted(families.items(), key=lambda x: -len(x[1])):
        print(f"  {fam_name}: {len(members)} controls")

    print("\n[3/4] Running promotion pipeline...")
    all_records: list[AdapterLegitimacyRecord] = []

    for fam_name, members in sorted(families.items(), key=lambda x: -len(x[1])):
        print(f"\n  --- Family: {fam_name} ({len(members)} controls) ---")
        fam_promoted = 0
        for contract in members:
            vid = contract["vuln_id"]
            evidence = extract_evidence_for_control_with_derivation(
                vid, matrix, manifest
            )
            binding = bundle.get(vid)
            record = run_fixture_suite(contract, evidence, binding)
            all_records.append(record)

            status = "PROMOTED" if record.promoted else f"{record.legitimacy_score}/9"
            dp = f"DP {record.dp_gates_passed}/{record.dp_gates_total}"
            sym = "+" if record.promoted else "."
            print(f"    [{sym}] {vid}: {status}  {dp}")
            if record.promoted:
                fam_promoted += 1
        print(f"  Family {fam_name}: {fam_promoted}/{len(members)} promoted")

    print("\n[4/4] Building export bundle...")
    export_bundle = build_export_bundle(all_records, contracts, matrix)
    output_path = write_export_bundle(export_bundle)
    print(f"  Written to: {output_path}")

    shippable = print_shipping_gate(export_bundle)

    elapsed = time.time() - start
    print(f"\n  Pipeline completed in {elapsed:.1f}s")

    legitimacy_path = REPO_ROOT / "bridge" / "LegitimacyRecords.json"
    records_data = {
        "record_kind": "AdapterLegitimacyRecords",
        "records": [r.to_dict() for r in all_records],
    }
    legitimacy_path.write_text(
        json.dumps(records_data, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"  Legitimacy records: {legitimacy_path}")

    if not shippable:
        sys.exit(0)


if __name__ == "__main__":
    run_pipeline()

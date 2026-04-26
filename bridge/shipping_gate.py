import json
from pathlib import Path

from bridge.verify_ep_gates import run_checks


ROOT = Path(__file__).resolve().parent.parent
EXPORT_BUNDLE_PATH = ROOT / "bridge" / "ExportBundle.json"
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"
LEGITIMACY_RECORDS_PATH = ROOT / "bridge" / "LegitimacyRecords.json"
EXPORT_HTML_PATH = ROOT / "export" / "stig_expert_critic.html"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_pass_rate(records, fixture_class):
    total = len(records)
    hits = 0
    for record in records:
        fixture = next(
            (item for item in record.get("fixture_results", []) if item["fixture_class"] == fixture_class),
            None,
        )
        if fixture and fixture.get("passed") is True:
            hits += 1
    return hits / total


def main():
    export_bundle = load_json(EXPORT_BUNDLE_PATH)
    projection_bundle = load_json(PROJECTION_BUNDLE_PATH)
    legitimacy_records = load_json(LEGITIMACY_RECORDS_PATH)
    records = legitimacy_records["records"]
    ep_summary = run_checks()
    total = export_bundle["summary"]["total"]
    promoted_count = export_bundle["summary"]["promoted"]
    unresolved_count = export_bundle["summary"]["projected_unresolved"]

    hard_gates = [
        ("HG-1", EXPORT_BUNDLE_PATH.exists() and export_bundle["record_kind"] == "ExportBundle", "ExportBundle valid"),
        ("HG-2", export_bundle["kill_switch_enforced"] is True, "Kill switch enforced"),
        ("HG-3", len(export_bundle["entries"]) == 67, "All 67 controls present"),
        ("HG-4", PROJECTION_BUNDLE_PATH.exists() and len(projection_bundle) == 67, "ProjectionBundle valid"),
        ("HG-5", EXPORT_HTML_PATH.exists() and EXPORT_HTML_PATH.stat().st_size != 0, "HTML export exists"),
        (
            "HG-6",
            all(
                item["verdict"] != "unresolved"
                for item in export_bundle["entries"]
                if item["status"] == "resolved"
            ),
            "Resolved controls are not unresolved",
        ),
        (
            "HG-7",
            all(
                item["live_validate_enabled"] is False
                for item in projection_bundle
                if item["display_status"] != "live_resolved"
            ),
            "Unresolved controls do not expose live validate",
        ),
        (
            "HG-8",
            all(len(item.get("provenance_chain", [])) >= 2 for item in export_bundle["entries"]),
            "Provenance present for export entries",
        ),
        (
            "HG-9",
            all(
                item["legitimacy"] == "9/9"
                for item in export_bundle["entries"]
                if item["status"] == "resolved"
            ),
            "Promoted entries have legitimacy 9/9",
        ),
        ("HG-10", ep_summary["passed"] == 12, "EP gates pass"),
    ]

    honest_unresolved = sum(
        1
        for item in projection_bundle
        if item["display_status"] != "live_resolved" and bool(item["explanation"])
    )
    metrics = {
        "M1 contract_coverage": promoted_count / total,
        "M2 fixture_coverage": sum(1 for item in records if item["legitimacy_score"] == 9) / total,
        "M3 dp_gate_coverage": sum(1 for item in records if item["dp_gates_passed"] == 10) / total,
        "M4 replay_fidelity": fixture_pass_rate(records, "good_minimal"),
        "M5 falsifier_rate": fixture_pass_rate(records, "bad_canonical"),
        "M6 boundary_fidelity": fixture_pass_rate(records, "boundary_value"),
        "M7 noise_immunity": fixture_pass_rate(records, "noisy_evidence"),
        "M8 scope_honesty": (promoted_count + honest_unresolved) / total,
    }

    all_hard_gates_pass = all(item[1] for item in hard_gates)
    waste_heat_ratio = unresolved_count / total
    shippable = (
        all_hard_gates_pass
        and waste_heat_ratio < 0.25
        and ep_summary["projection_equivalence_rate"] == 1.0
        and ep_summary["unresolved_preservation_rate"] == 1.0
        and ep_summary["scope_fidelity_rate"] == 1.0
        and ep_summary["role_drift_incidents"] == 0
        and ep_summary["frontend_truth_invention_incidents"] == 0
    )

    print("============================================================")
    print("  SHIPPING GATE EVALUATION")
    print("============================================================")
    print()
    print("  HARD GATES")
    for gate_id, ok, detail in hard_gates:
        print(f"  {gate_id}:  {'PASS' if ok else 'FAIL'}  {detail}")
    print()
    print("  MATURITY METRICS")
    for label, value in metrics.items():
        print(f"  {label}:".ljust(32) + f"{value:0.3f}")
    print()
    print("  AGGREGATE THRESHOLDS")
    print(
        "  projection_equivalence_rate:".ljust(40)
        + f"{ep_summary['projection_equivalence_rate']:.3f}  "
        + ("PASS" if ep_summary["projection_equivalence_rate"] == 1.0 else "FAIL")
    )
    print(
        "  unresolved_preservation_rate:".ljust(40)
        + f"{ep_summary['unresolved_preservation_rate']:.3f}  "
        + ("PASS" if ep_summary["unresolved_preservation_rate"] == 1.0 else "FAIL")
    )
    print(
        "  scope_fidelity_rate:".ljust(40)
        + f"{ep_summary['scope_fidelity_rate']:.3f}  "
        + ("PASS" if ep_summary["scope_fidelity_rate"] == 1.0 else "FAIL")
    )
    print(
        "  role_drift_incidents:".ljust(40)
        + f"{ep_summary['role_drift_incidents']}      "
        + ("PASS" if ep_summary["role_drift_incidents"] == 0 else "FAIL")
    )
    print(
        "  frontend_truth_invention_incidents:".ljust(40)
        + f"{ep_summary['frontend_truth_invention_incidents']}      "
        + ("PASS" if ep_summary["frontend_truth_invention_incidents"] == 0 else "FAIL")
    )
    print()
    print("  SHIPPING GATE")
    print(f"  waste_heat_ratio: {waste_heat_ratio:.3f} (threshold: < 0.25)")
    print(f"  RESULT: {'SHIPPABLE' if shippable else 'NOT SHIPPABLE'}")
    print("============================================================")
    if not shippable:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

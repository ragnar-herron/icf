import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPORT_BUNDLE_PATH = ROOT / "bridge" / "ExportBundle.json"
CONTRACTS_PATH = ROOT / "rebuild_kit" / "domain_data" / "assertion_contracts.json"
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"

REQUIRED_FIELDS = [
    "vuln_id",
    "display_status",
    "stig_verdict",
    "severity",
    "title",
    "evidence_summary",
    "pullback_row",
    "legitimacy",
    "dp_gates",
    "provenance",
    "remediation",
    "explanation",
    "live_validate_enabled",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_contracts(path: Path):
    payload = load_json(path)
    contracts = payload.get("contracts", [])
    return {item["vuln_id"]: item for item in contracts}


def derive_display_status(entry):
    if entry["status"] == "resolved":
        return "live_resolved"
    provenance = entry.get("provenance_chain", [])
    if any("blocked-external" in item for item in provenance):
        return "blocked_external"
    if any("was: fail" in item for item in provenance):
        return "open_finding"
    return "pending_promotion"


def derive_projection_entry(entry, contracts_by_vid):
    contract = contracts_by_vid.get(entry["vuln_id"], {})
    display_status = derive_display_status(entry)
    if display_status == "live_resolved":
        stig_verdict = entry["verdict"]
        evidence_summary = (entry.get("pullback_row") or {}).get("observed")
        pullback_row = entry.get("pullback_row")
        explanation = None
        live_validate_enabled = True
    elif display_status == "blocked_external":
        stig_verdict = "unresolved"
        evidence_summary = None
        pullback_row = None
        explanation = (
            "Requires organization-provided evidence not available from the appliance. "
            f"Adapter not promoted ({entry['legitimacy']})."
        )
        live_validate_enabled = False
    elif display_status == "open_finding":
        stig_verdict = "open"
        evidence_summary = None
        pullback_row = None
        explanation = (
            "Real evidence fails this control. "
            f"Adapter not promoted ({entry['legitimacy']})."
        )
        live_validate_enabled = False
    else:
        stig_verdict = "unresolved"
        evidence_summary = None
        pullback_row = None
        explanation = (
            "Live evidence passes but adapter fixture suite incomplete "
            f"({entry['legitimacy']}). Awaiting promotion."
        )
        live_validate_enabled = False

    return {
        "vuln_id": entry["vuln_id"],
        "display_status": display_status,
        "stig_verdict": stig_verdict,
        "severity": contract.get("severity"),
        "title": contract.get("rule_title") or contract.get("title"),
        "evidence_summary": evidence_summary,
        "pullback_row": pullback_row,
        "legitimacy": entry["legitimacy"],
        "dp_gates": entry["dp_gates"],
        "provenance": entry.get("provenance_chain", []),
        "remediation": contract.get("remediation"),
        "explanation": explanation,
        "live_validate_enabled": live_validate_enabled,
    }


def build_projection_bundle(
    export_bundle_path: Path = EXPORT_BUNDLE_PATH,
    contracts_path: Path = CONTRACTS_PATH,
):
    export_bundle = load_json(export_bundle_path)
    contracts_by_vid = load_contracts(contracts_path)
    entries = export_bundle.get("entries", [])
    return [
        derive_projection_entry(entry, contracts_by_vid)
        for entry in entries
    ]


def write_projection_bundle(
    output_path: Path = PROJECTION_BUNDLE_PATH,
    export_bundle_path: Path = EXPORT_BUNDLE_PATH,
    contracts_path: Path = CONTRACTS_PATH,
):
    projection_bundle = build_projection_bundle(
        export_bundle_path=export_bundle_path,
        contracts_path=contracts_path,
    )
    output_path.write_text(
        json.dumps(projection_bundle, indent=2),
        encoding="utf-8",
    )
    return projection_bundle


def run_self_test(
    projection_bundle,
    export_bundle_path: Path = EXPORT_BUNDLE_PATH,
):
    export_bundle = load_json(export_bundle_path)
    export_entries = {item["vuln_id"]: item for item in export_bundle.get("entries", [])}

    assert len(projection_bundle) == 67
    counts = {
        "live_resolved": 0,
        "blocked_external": 0,
        "open_finding": 0,
        "pending_promotion": 0,
    }
    for item in projection_bundle:
        for field_name in REQUIRED_FIELDS:
            assert field_name in item, f"missing field: {field_name}"
        if item["live_validate_enabled"]:
            assert item["display_status"] == "live_resolved"
        if export_entries[item["vuln_id"]]["status"] == "projected_unresolved":
            assert item["display_status"] != "live_resolved"
        counts[item["display_status"]] += 1

    assert counts["live_resolved"] == 60
    assert counts["blocked_external"] == 5
    assert counts["open_finding"] == 2
    assert counts["pending_promotion"] == 0
    return counts


def main():
    projection_bundle = write_projection_bundle()
    counts = run_self_test(projection_bundle)
    print(f"ProjectionBundle.json written with {len(projection_bundle)} entries")
    print(
        "live_resolved: {live_resolved}, blocked_external: {blocked_external}, "
        "open_finding: {open_finding}, pending_promotion: {pending_promotion}".format(
            **counts
        )
    )
    print("All self-test assertions passed")


if __name__ == "__main__":
    main()

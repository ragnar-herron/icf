"""
bridge/export_bundler.py

Packages promoted adapter results into ExportBundle.json for the HTML export.
Enforces the system-level kill switch: if an adapter is not promoted,
the bundle entry says projected_unresolved, period.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.fixture_runner import AdapterLegitimacyRecord

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ExportEntry:
    vuln_id: str
    status: str  # "resolved" or "projected_unresolved"
    verdict: str  # "pass", "fail", "not_a_finding", "open", or "unresolved"
    evidence_ref: str
    pullback_row: dict[str, Any] | None
    legitimacy: str
    dp_gates: str
    provenance_chain: list[str]


def build_export_bundle(
    records: list[AdapterLegitimacyRecord],
    contracts: list[dict],
    matrix: dict,
) -> dict:
    """Build the ExportBundle from legitimacy records.

    KILL SWITCH: Any control without 9/9 legitimacy gets
    status=projected_unresolved. No exceptions.
    """
    contract_map = {c["vuln_id"]: c for c in contracts}
    disposition_map = {}
    for outcome in matrix["outcomes"]:
        disposition_map[outcome["vuln_id"]] = outcome["disposition"]

    entries: list[dict] = []
    promoted_count = 0
    unresolved_count = 0

    for record in records:
        vid = record.vuln_id
        contract = contract_map.get(vid, {})
        live_disposition = disposition_map.get(vid, "unknown")

        if record.promoted:
            good_fixture = None
            for fr in record.fixture_results:
                if fr.fixture_class == "good_minimal":
                    good_fixture = fr
                    break

            verdict = good_fixture.actual_verdict if good_fixture else "unresolved"
            stig_verdict = {
                "pass": "not_a_finding",
                "fail": "open",
            }.get(verdict, "unresolved")

            entry = ExportEntry(
                vuln_id=vid,
                status="resolved",
                verdict=stig_verdict,
                evidence_ref=f"live_state/full_campaign -> {vid}",
                pullback_row=good_fixture.row.to_dict() if good_fixture else None,
                legitimacy=f"{record.legitimacy_score}/{record.legitimacy_max}",
                dp_gates=f"{record.dp_gates_passed}/{record.dp_gates_total}",
                provenance_chain=[
                    f"assertion_contracts.json -> {vid}",
                    f"FactoryDistinctionBundle.json -> {vid}",
                    f"LiveControlOutcomeMatrix.json -> {vid}",
                    f"bridge/promote_all.py -> 9/9 legitimacy verified",
                ],
            )
            promoted_count += 1
        else:
            entry = ExportEntry(
                vuln_id=vid,
                status="projected_unresolved",
                verdict="unresolved",
                evidence_ref=f"live_state/full_campaign -> {vid}",
                pullback_row=None,
                legitimacy=f"{record.legitimacy_score}/{record.legitimacy_max}",
                dp_gates=f"{record.dp_gates_passed}/{record.dp_gates_total}",
                provenance_chain=[
                    f"assertion_contracts.json -> {vid}",
                    f"KILL SWITCH: adapter not promoted ({record.legitimacy_score}/9)",
                    f"live disposition was: {live_disposition}",
                ],
            )
            unresolved_count += 1

        entries.append(asdict(entry))

    bundle = {
        "record_kind": "ExportBundle",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "invariant": "Projection coalgebra may not exist unless Adapter coalgebra is promoted.",
        "kill_switch_enforced": True,
        "summary": {
            "total": len(records),
            "promoted": promoted_count,
            "projected_unresolved": unresolved_count,
        },
        "entries": entries,
    }
    return bundle


def write_export_bundle(
    bundle: dict,
    output_path: Path | None = None,
) -> Path:
    if output_path is None:
        output_path = REPO_ROOT / "bridge" / "ExportBundle.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path


def print_shipping_gate(bundle: dict) -> bool:
    """Print the shipping gate summary. Returns True if shippable."""
    summary = bundle["summary"]
    total = summary["total"]
    promoted = summary["promoted"]
    unresolved = summary["projected_unresolved"]

    print("\n" + "=" * 60)
    print("  SHIPPING GATE SUMMARY")
    print("=" * 60)
    print(f"  Total controls:         {total}")
    print(f"  Promoted (9/9 + DP 10): {promoted}")
    print(f"  Projected unresolved:   {unresolved}")
    print(f"  Kill switch enforced:   {bundle['kill_switch_enforced']}")

    shippable = unresolved == 0
    if shippable:
        print("\n  GATE: PASS - all controls promoted, safe to ship")
    else:
        pct = (promoted / total * 100) if total else 0
        print(f"\n  GATE: HOLD - {unresolved} controls unresolved ({pct:.0f}% promoted)")
        print("  Unresolved controls cannot be shipped as resolved.")
        print("  They will appear as projected_unresolved in the export.")

    print("=" * 60)
    return shippable


if __name__ == "__main__":
    print("export_bundler.py: use via promote_all.py")

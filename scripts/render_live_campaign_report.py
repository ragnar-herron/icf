#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "coalgebra" / "stig_expert_critic" / "ControlCatalog.json"
OUTCOMES = REPO / "coalgebra" / "stig_expert_critic" / "LiveControlOutcomeMatrix.json"
MANIFEST = REPO / "live_state" / "full_campaign" / "manifest.json"
EVIDENCE = REPO / "coalgebra" / "stig_expert_critic" / "LiveCampaignEvidence.json"
EXTERNAL_PACKAGES = REPO / "coalgebra" / "stig_expert_critic" / "ExternalEvidencePackages.json"
REPORT = REPO / "docs" / "LIVE_RUN_REPORT.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    catalog = load(CATALOG)
    outcomes = load(OUTCOMES)
    manifest = load(MANIFEST)
    external_packages = load(EXTERNAL_PACKAGES) if EXTERNAL_PACKAGES.exists() else {"packages": []}

    title_by_vid = {control["vuln_id"]: control["title"] for control in catalog["controls"]}
    rows = outcomes["outcomes"]
    summary = outcomes["disposition_summary"]

    evidence = {
        "record_kind": "LiveCampaignEvidence",
        "subject": "stig_expert_critic_p0a",
        "host": outcomes["host"],
        "hostname": outcomes["hostname"],
        "tmos_version": outcomes["tmos_version"],
        "control_count": len(rows),
        "disposition_summary": summary,
        "artifacts": {
            "control_catalog": "coalgebra/stig_expert_critic/ControlCatalog.json",
            "outcome_matrix": "coalgebra/stig_expert_critic/LiveControlOutcomeMatrix.json",
            "snapshots_manifest": "live_state/full_campaign/manifest.json",
            "external_evidence_packages": "coalgebra/stig_expert_critic/ExternalEvidencePackages.json",
            "campaign_ledger": "ledgers/live/full_campaign.jsonl",
        },
        "snapshots": {
            "count": len(manifest["snapshots"]),
            "blob_paths": [snapshot["blob_path"] for snapshot in manifest["snapshots"]],
        },
        "notable_remediations": [
            {
                "vuln_id": "V-266070",
                "action": "Applied the canonical DoD Notice and Consent Banner to TMOS UI login banner via /mgmt/tm/sys/global-settings.",
            },
            {
                "vuln_id": "V-266066/V-266067",
                "action": "Reduced the local `stig_operator` account from `admin` to `auditor`, leaving one local admin account of last resort and aligning local role assignment more closely with least privilege.",
            }
        ],
        "remaining_failures": [
            row["vuln_id"] for row in rows if row["disposition"] == "fail"
        ],
        "remaining_blocked_external": [
            row["vuln_id"] for row in rows if row["disposition"] == "blocked-external"
        ],
        "production_gaps_live": [
            "Some controls remain blocked on external identity, PKI, organizational policy, or storage topology inputs that cannot be inferred from the appliance alone.",
            "The campaign ledger records final per-control dispositions and evidence blobs, and the remaining local failures are now narrowed to one actual platform certificate issue and one remote-access always-on VPN issue.",
            "Repo-side external evidence packages are now part of the replayed artifact set, but several blocked rows still require owner-supplied SSP, PKI, backup-topology, or service-authorization evidence.",
        ],
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    by_disposition = {
        key: [row for row in rows if row["disposition"] == key]
        for key in ["pass", "fail", "not-applicable", "blocked-external"]
    }

    lines: list[str] = []
    lines.append("# STIG Expert Critic — Live Full Campaign Report")
    lines.append("")
    lines.append(
        f"This report records the full live STIG campaign run against `{outcomes['hostname']}` "
        f"at `{outcomes['host']}` (TMOS `{outcomes['tmos_version']}`)."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Controls in scope: **{len(rows)}**")
    lines.append(f"- Pass: **{summary.get('pass', 0)}**")
    lines.append(f"- Fail: **{summary.get('fail', 0)}**")
    lines.append(f"- Not applicable: **{summary.get('not-applicable', 0)}**")
    lines.append(f"- Blocked external: **{summary.get('blocked-external', 0)}**")
    lines.append(f"- Snapshot artifacts: **{len(manifest['snapshots'])}**")
    lines.append("- Campaign ledger: `ledgers/live/full_campaign.jsonl`")
    lines.append(f"- External evidence packages: **{len(external_packages.get('packages', []))}**")
    lines.append("")
    lines.append("## What changed live")
    lines.append("")
    lines.append(
        "- `V-266070` was actively remediated on the device by replacing the placeholder TMOS login banner with the full canonical DoD Notice and Consent banner."
    )
    lines.append(
        "- The local `stig_operator` account was demoted from `admin` to `auditor`, leaving a single local admin account of last resort and closing the local role-assignment/admin fallback findings."
    )
    lines.append(
        "- The campaign was then re-snapshotted and rebuilt from the new live state, with repo-side external evidence packages attached for the remaining true external blockers."
    )
    lines.append("")
    lines.append("## Per-Control Outcomes")
    lines.append("")
    lines.append("| V-ID | Disposition | Title | Rationale |")
    lines.append("| --- | --- | --- | --- |")
    for row in rows:
        title = title_by_vid.get(row["vuln_id"], "")
        rationale = row["rationale"].replace("|", "\\|")
        title = title.replace("|", "\\|")
        lines.append(
            f"| `{row['vuln_id']}` | `{row['disposition']}` | {title} | {rationale} |"
        )
    lines.append("")
    lines.append("## Remaining Non-Pass Controls")
    lines.append("")
    for key in ["fail", "not-applicable", "blocked-external"]:
        lines.append(f"### `{key}`")
        lines.append("")
        for row in by_disposition[key]:
            lines.append(
                f"- `{row['vuln_id']}` — {title_by_vid.get(row['vuln_id'], '')}: {row['rationale']}"
            )
        if not by_disposition[key]:
            lines.append("- none")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {EVIDENCE}")
    print(f"wrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

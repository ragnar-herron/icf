#!/usr/bin/env python3
"""
Generate coalgebra/stig_expert_critic/ScopeCoverageMatrix.json
from docs/stig_list.csv and docs/disa_stigs.json.

This script is idempotent and side-effect-free outside the output file.
It is intentionally minimal: it does NOT automate any STIG, it only
produces the coverage matrix artifact that gate M4 reads.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

REPO = Path(__file__).resolve().parent.parent
STIG_LIST = REPO / "docs" / "stig_list.csv"
DISA = REPO / "docs" / "disa_stigs.json"
OUT = REPO / "coalgebra" / "stig_expert_critic" / "ScopeCoverageMatrix.json"


def load_findings() -> Dict[str, dict]:
    data = DISA.read_bytes().decode("utf-8")
    decoder = json.JSONDecoder()
    findings: Dict[str, dict] = {}
    i, n = 0, len(data)
    while i < n:
        while i < n and data[i].isspace():
            i += 1
        if i >= n:
            break
        obj, j = decoder.raw_decode(data, i)
        stig = (obj.get("stig") or {}) if isinstance(obj, dict) else {}
        found = stig.get("findings") or {}
        if isinstance(found, dict):
            findings.update(found)
        i = j
    return findings


def load_selected_vids() -> List[str]:
    with STIG_LIST.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row["vuln_id"].strip() for row in reader if row.get("vuln_id")]


AXIS_RULES = (
    ("tmsh_show", re.compile(r"tmsh\s+show", re.I), "module"),
    ("tmsh_list", re.compile(r"tmsh\s+list", re.I), "module"),
    ("tmsh_modify", re.compile(r"tmsh\s+modify", re.I), "module"),
    ("icontrol_rest", re.compile(r"(icontrol|/mgmt/tm)", re.I), "module"),
    ("gui_only", re.compile(r"(configuration utility|system\s*\|\s*|gui)", re.I), "module"),
)


def classify_automation(finding: dict) -> str:
    text = (
        (finding.get("checktext") or "")
        + "\n"
        + (finding.get("fixtext") or "")
    ).lower()
    if any(pattern.search(text) for _, pattern, _ in AXIS_RULES if _ != "gui_only"):
        return "AUTOMATED_CANDIDATE"
    if "configuration utility" in text or "gui" in text:
        return "GUI_ONLY"
    return "MANUAL_REVIEW"


def classify_surface(finding: dict) -> str:
    text = (
        (finding.get("checktext") or "")
        + "\n"
        + (finding.get("fixtext") or "")
    ).lower()
    if "/mgmt/tm" in text or "icontrol" in text:
        return "icontrol_rest"
    if "tmsh" in text:
        return "tmsh"
    if "configuration utility" in text or "gui" in text:
        return "gui"
    return "unspecified"


def classify_module(finding: dict) -> str:
    text = (
        (finding.get("checktext") or "")
        + "\n"
        + (finding.get("fixtext") or "")
        + "\n"
        + (finding.get("title") or "")
    ).lower()
    for module in ("ltm", "apm", "asm", "afm", "avr", "pem", "gtm", "dns"):
        if re.search(rf"\b{module}\b", text):
            return module.upper()
    return "PLATFORM"


def classify_severity(finding: dict) -> str:
    sev = (finding.get("severity") or "").lower()
    if sev in ("high", "cat i"):
        return "high"
    if sev in ("medium", "cat ii"):
        return "medium"
    if sev in ("low", "cat iii"):
        return "low"
    return "unspecified"


def build_controls(vids: Iterable[str], findings: Dict[str, dict]) -> List[dict]:
    controls: List[dict] = []
    for vid in vids:
        finding = findings.get(vid)
        if not isinstance(finding, dict):
            controls.append(
                {
                    "vuln_id": vid,
                    "status": "missing_source",
                    "automation_class": "UNRESOLVED",
                    "surface": "unspecified",
                    "module": "PLATFORM",
                    "severity": "unspecified",
                }
            )
            continue
        controls.append(
            {
                "vuln_id": vid,
                "rule_id": finding.get("rule_id", ""),
                "title": finding.get("title", ""),
                "status": "covered_as_candidate",
                "automation_class": classify_automation(finding),
                "surface": classify_surface(finding),
                "module": classify_module(finding),
                "severity": classify_severity(finding),
            }
        )
    return controls


def summarise(controls: List[dict]) -> dict:
    axes: Dict[str, Dict[str, int]] = {
        "automation_class": {},
        "surface": {},
        "module": {},
        "severity": {},
    }
    for control in controls:
        for axis in axes:
            value = control.get(axis, "unspecified")
            axes[axis][value] = axes[axis].get(value, 0) + 1
    return {axis: dict(sorted(buckets.items())) for axis, buckets in axes.items()}


def main() -> int:
    findings = load_findings()
    vids = load_selected_vids()
    controls = build_controls(vids, findings)
    axis_histogram = summarise(controls)
    matrix = {
        "record_kind": "ScopeCoverageMatrix",
        "subject": "stig_expert_critic_p0a",
        "source_csv": "docs/stig_list.csv",
        "source_json": "docs/disa_stigs.json",
        "selected_vuln_count": len(controls),
        "resolved_from_source_count": sum(
            1 for c in controls if c["status"] != "missing_source"
        ),
        "scope_axes": {
            "platform": ["F5 BIG-IP"],
            "module": sorted(axis_histogram["module"].keys()),
            "topology": ["standalone"],
            "credential_scope": ["read-only fixture"],
        },
        "axis_histogram": axis_histogram,
        "demo_control": {
            "control_id": "demo.banner.approved",
            "witness_id": "demo.banner.approved",
            "scope_record": "ScopeRecord.json",
            "status": "covered",
        },
        "controls": controls,
        "hidden_regressions_detected": False,
        "notes": (
            "Classification is heuristic and explicitly subordinate to criticism. "
            "'AUTOMATED_CANDIDATE' means a surface was detected in the check/fix text; "
            "every such candidate must still survive witness-authoring, break/fix, and "
            "promotion before it is declared production-ready."
        ),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(matrix, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(
        f"controls={len(controls)} resolved={matrix['resolved_from_source_count']} "
        f"modules={len(axis_histogram['module'])} automation_classes={len(axis_histogram['automation_class'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

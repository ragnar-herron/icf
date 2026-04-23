from __future__ import annotations

import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

TARGETS = [
    ROOT / "web_app.py",
    ROOT / "capture_runner.py",
    ROOT / "live_evaluator.py",
    ROOT / "stig_remediation_tool.html",
]

FORBIDDEN_PATTERNS = [
    {
        "id": "per_control_evaluator",
        "description": "Per-control evaluators at the export boundary are forbidden.",
        "pattern": re.compile(r"def\s+evaluate_v\d+", re.MULTILINE),
    },
    {
        "id": "ui_tmsh_parsing",
        "description": "The UI must not parse tmsh output directly.",
        "pattern": re.compile(r"extract_from_tmsh|tmsh_property_candidates"),
        "files": {"stig_remediation_tool.html"},
    },
]

GRANDFATHERED_EXCEPTIONS = {
    "per_control_evaluator": {
        "live_evaluator.py": [
            "def evaluate_v266095",
            "def evaluate_v266170",
        ]
    },
    "ui_tmsh_parsing": {
        "live_evaluator.py": [],
    },
}


def enforcement_summary() -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    grandfathered: list[dict[str, str]] = []
    for target in TARGETS:
        text = target.read_text(encoding="utf-8")
        for rule in FORBIDDEN_PATTERNS:
            files = rule.get("files")
            if files and target.name not in files:
                continue
            for match in rule["pattern"].finditer(text):
                snippet = match.group(0)
                allowed = snippet in GRANDFATHERED_EXCEPTIONS.get(rule["id"], {}).get(target.name, [])
                item = {
                    "rule_id": rule["id"],
                    "file": target.name,
                    "snippet": snippet,
                    "description": rule["description"],
                }
                if allowed:
                    grandfathered.append(item)
                else:
                    violations.append(item)
    return {
        "status": "pass" if not violations else "fail",
        "violations": violations,
        "grandfathered": grandfathered,
        "summary": (
            "No unapproved boundary violations detected."
            if not violations
            else f"{len(violations)} unapproved boundary violation(s) detected."
        ),
    }

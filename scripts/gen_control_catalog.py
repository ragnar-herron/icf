#!/usr/bin/env python3
"""
Generate a machine-readable live STIG control catalog from `docs/stig_list.csv`
and `docs/disa_stigs.json`.

The catalog is intentionally heuristic. It does not claim a control is
automatically satisfiable; it captures what the repo currently knows about each
V-ID so the live campaign can classify it honestly as pass/fail/not-applicable/
blocked-external on this specific appliance.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

REPO = Path(__file__).resolve().parent.parent
STIG_LIST = REPO / "docs" / "stig_list.csv"
DISA = REPO / "docs" / "disa_stigs.json"
ASSERTIONS = REPO / "docs" / "assertion_contracts.json"
OUT = REPO / "coalgebra" / "stig_expert_critic" / "ControlCatalog.json"


def load_findings() -> Dict[str, dict]:
    data = DISA.read_text(encoding="utf-8")
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


def load_assertion_contracts() -> Dict[str, dict]:
    if not ASSERTIONS.exists():
        return {}
    doc = json.loads(ASSERTIONS.read_text(encoding="utf-8"))
    contracts: Dict[str, dict] = {}
    for contract in doc.get("contracts", []):
        vid = contract.get("vuln_id")
        if vid:
            contracts[vid] = contract
    return contracts


def lower_text(finding: dict) -> str:
    return "\n".join(
        [
            finding.get("title", ""),
            finding.get("checktext", ""),
            finding.get("fixtext", ""),
            finding.get("description", ""),
        ]
    ).lower()


def classify_module(text: str) -> str:
    if "access." in text or "apm " in text or "access profile" in text:
        return "APM"
    if "application security" in text or "asm" in text or "waf" in text:
        return "ASM"
    if "firewall" in text or "afm" in text:
        return "AFM"
    if "dns" in text or "gtm" in text:
        return "DNS"
    if "local traffic" in text or "virtual server" in text or "ssl profile" in text:
        return "LTM"
    return "PLATFORM"


def classify_surface(text: str) -> str:
    if "tmsh " in text:
        return "tmsh"
    if "/mgmt/tm" in text or "icontrol" in text:
        return "icontrol_rest"
    if "gui" in text or "configuration utility" in text:
        return "gui"
    return "unspecified"


def classify_evidence_kind(text: str) -> str:
    if "verify" in text and ("is checked" in text or "is selected" in text):
        return "boolean_presence"
    if any(token in text for token in ["set to", "configured to use", "must be exactly"]):
        return "field_equality"
    if any(token in text for token in ["at least", "minimum", "maximum", "limit", "threshold"]):
        return "numeric_threshold"
    if any(token in text for token in ["review the list", "verify the list", "repeat for other"]):
        return "list_membership"
    if any(
        token in text
        for token in ["document this process", "issm", "isso", "policy", "organization-defined"]
    ):
        return "external_attestation"
    return "field_predicate"


def classify_handler_family(text: str) -> str:
    if "security banner text to show on the login screen" in text:
        return "banner"
    if "password-policy" in text or "maximum login failures" in text or "lockout" in text:
        return "password_policy"
    if "access profile" in text or "apm" in text or "profiles/policies" in text:
        return "apm_access"
    if "application security" in text or "attack signatures" in text:
        return "asm_policy"
    if "firewall" in text or "network firewall" in text:
        return "afm_firewall"
    if "virtual server" in text and any(
        token in text
        for token in [
            "ports, protocols",
            "ports/protocols",
            "prohibited ports",
            "unnecessary and/or nonsecure",
            "ppsm",
        ]
    ):
        return "ltm_virtual_services"
    if "virtual server" in text or "ssl profile" in text:
        return "ltm_virtual_ssl"
    if "syslog" in text or "remote log" in text or "event log" in text:
        return "logging"
    if "ntp" in text or "time server" in text:
        return "ntp"
    if "snmp" in text:
        return "snmp"
    if "sshd" in text or "ssh" in text:
        return "sshd"
    if "save sys ucs" in text or "archives" in text or "backup" in text:
        return "backup"
    return "manual_or_generic"


def extract_applicability_clause(checktext: str) -> Tuple[bool, str]:
    for line in checktext.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("if ") and "not applicable" in stripped.lower():
            return True, stripped
    return False, ""


READ_PATH_RULES: Tuple[Tuple[str, List[str]], ...] = (
    ("banner", ["/mgmt/tm/sys/global-settings", "/mgmt/tm/sys/sshd"]),
    ("password_policy", ["/mgmt/tm/auth/password-policy"]),
    ("apm_access", ["/mgmt/tm/apm/profile/access", "/mgmt/tm/apm/log-setting"]),
    ("asm_policy", ["/mgmt/tm/asm/policies", "/mgmt/tm/ltm/virtual"]),
    ("afm_firewall", ["/mgmt/tm/security/firewall/policy", "/mgmt/tm/ltm/virtual"]),
    ("ltm_virtual_services", ["/mgmt/tm/ltm/virtual"]),
    ("ltm_virtual_ssl", ["/mgmt/tm/ltm/virtual", "/mgmt/tm/ltm/profile/client-ssl"]),
    ("logging", ["/mgmt/tm/sys/syslog", "/mgmt/tm/apm/log-setting"]),
    ("ntp", ["/mgmt/tm/sys/ntp"]),
    ("snmp", ["/mgmt/tm/sys/snmp"]),
    ("sshd", ["/mgmt/tm/sys/sshd", "/mgmt/tm/sys/global-settings"]),
    ("backup", ["/mgmt/tm/sys/ucs"]),
    ("manual_or_generic", ["/mgmt/tm/sys/provision"]),
)


def candidate_read_paths(handler_family: str) -> List[str]:
    for family, paths in READ_PATH_RULES:
        if handler_family == family:
            return paths
    return ["/mgmt/tm/sys/provision"]


def classify_outcome_class(text: str, handler_family: str, module: str) -> str:
    if "issm" in text or "isso" in text or "ppsm" in text:
        return "external-dependency"
    if "organization-defined" in text and handler_family not in {
        "password_policy",
        "banner",
        "sshd",
    }:
        return "external-dependency"
    if "ocsp" in text or "crldp" in text or "mfa" in text or "syslog server" in text:
        return "external-dependency"
    if handler_family == "manual_or_generic":
        return "manual-evidence"
    if module in {"APM", "ASM", "AFM", "LTM", "DNS", "PLATFORM"}:
        return "automatable"
    return "manual-evidence"


def build_control(vid: str, finding: dict, contract: dict | None = None) -> dict:
    text = lower_text(finding)
    conditional_na, applicability_clause = extract_applicability_clause(
        finding.get("checktext", "")
    )
    module = classify_module(text)
    handler_family = classify_handler_family(text)
    source_payload = {
        "vuln_id": vid,
        "ruleID": finding.get("ruleID", ""),
        "checkid": finding.get("checkid", ""),
        "fixid": finding.get("fixid", ""),
        "title": finding.get("title", ""),
        "checktext": finding.get("checktext", ""),
        "fixtext": finding.get("fixtext", ""),
        "description": finding.get("description", ""),
        "severity": finding.get("severity", ""),
    }
    source_sha256 = hashlib.sha256(
        json.dumps(source_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    control = {
        "vuln_id": vid,
        "rule_id": finding.get("ruleID", ""),
        "check_id": finding.get("checkid", ""),
        "fix_id": finding.get("fixid", ""),
        "title": finding.get("title", ""),
        "severity": (finding.get("severity") or "").lower(),
        "module": module,
        "surface": classify_surface(text),
        "evidence_kind": classify_evidence_kind(text),
        "handler_family": handler_family,
        "candidate_read_paths": candidate_read_paths(handler_family),
        "candidate_write_paths": candidate_read_paths(handler_family),
        "conditional_not_applicable": conditional_na,
        "applicability_clause": applicability_clause,
        "expected_outcome_class": classify_outcome_class(text, handler_family, module),
        "tmsh_tokens": sorted(
            set(re.findall(r"tmsh\s+(?:list|show|modify|save)\s+[^\n]+", text, re.I))
        )[:8],
        "key_tokens": sorted(
            {
                token
                for token in [
                    "mfa",
                    "ocsp",
                    "crldp",
                    "syslog",
                    "ntp",
                    "snmp",
                    "banner",
                    "ssh",
                    "access profile",
                    "attack signatures",
                    "virtual server",
                    "backup",
                ]
                if token in text
            }
        ),
        "source_stig": {
            **source_payload,
            "source_json": "docs/disa_stigs.json",
            "source_sha256": source_sha256,
        },
    }
    if contract:
        control.update(
            {
                "assertion_id": contract.get("assertion_id", ""),
                "evidence_required": contract.get("evidence_required", []),
                "criteria": contract.get("criteria", {}),
                "validation_method": contract.get("validation_method", ""),
                "tmsh_commands": contract.get("tmsh_commands", []),
                "rest_endpoints": contract.get("rest_endpoints", []),
                "remediation": contract.get("remediation", {}),
                "runtime_family": contract.get("runtime_family", ""),
                "organization_policy": contract.get("organization_policy", {}),
                "assertion_contract": {
                    "source_json": "docs/assertion_contracts.json",
                    "assertion_id": contract.get("assertion_id", ""),
                    "review_status": (contract.get("provenance") or {}).get("review_status", ""),
                    "selected_preferred_source": (contract.get("provenance") or {}).get(
                        "selected_preferred_source", ""
                    ),
                },
            }
        )
        if contract.get("validation_method") == "tmsh":
            control["surface"] = "tmsh"
        if control.get("evidence_required") == ["virtual_server_services_restricted"]:
            control["evidence_kind"] = "list_membership"
            control["handler_family"] = "ltm_virtual_services"
            control["candidate_read_paths"] = contract.get("rest_endpoints") or ["/mgmt/tm/ltm/virtual"]
            control["candidate_write_paths"] = contract.get("rest_endpoints") or ["/mgmt/tm/ltm/virtual"]
            control["expected_outcome_class"] = "automatable"
    return control


def build_controls(
    vids: Iterable[str],
    findings: Dict[str, dict],
    assertion_contracts: Dict[str, dict],
) -> List[dict]:
    controls: List[dict] = []
    for vid in vids:
        finding = findings.get(vid)
        if not isinstance(finding, dict):
            controls.append(
                {
                    "vuln_id": vid,
                    "status": "missing_source",
                    "expected_outcome_class": "manual-evidence",
                }
            )
            continue
        controls.append(build_control(vid, finding, assertion_contracts.get(vid)))
    return controls


def summarize(controls: List[dict]) -> dict:
    keys = [
        "module",
        "surface",
        "evidence_kind",
        "handler_family",
        "expected_outcome_class",
        "severity",
    ]
    buckets: Dict[str, Dict[str, int]] = {key: {} for key in keys}
    conditional_na = 0
    for control in controls:
        if control.get("conditional_not_applicable"):
            conditional_na += 1
        for key in keys:
            value = str(control.get(key, "unspecified"))
            buckets[key][value] = buckets[key].get(value, 0) + 1
    summary = {key: dict(sorted(values.items())) for key, values in buckets.items()}
    summary["conditional_not_applicable"] = conditional_na
    return summary


def main() -> int:
    findings = load_findings()
    assertion_contracts = load_assertion_contracts()
    vids = load_selected_vids()
    controls = build_controls(vids, findings, assertion_contracts)
    catalog = {
        "record_kind": "ControlCatalog",
        "subject": "stig_expert_critic_p0a",
        "source_csv": "docs/stig_list.csv",
        "source_json": "docs/disa_stigs.json",
        "assertion_contracts_json": "docs/assertion_contracts.json",
        "control_count": len(controls),
        "summary": summarize(controls),
        "notes": [
            "This file is heuristic and is generated from DISA text, not from live device state.",
            "expected_outcome_class is a planning hint, not a compliance verdict.",
            "The live campaign must still classify each control on the actual device as pass/fail/not-applicable/blocked-external.",
        ],
        "controls": controls,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"controls={len(controls)} conditional_na={catalog['summary']['conditional_not_applicable']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

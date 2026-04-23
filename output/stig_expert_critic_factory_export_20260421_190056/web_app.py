#!/usr/bin/env python3
"""
STIG Expert-Critic factory web application (standalone).

This single-file server is the *exported* interface to the F5 BIG-IP STIG
expert/critic factory. It is fully self-contained inside this folder --
no imports outside this directory -- so the whole folder can be copied or
published as an atomic artefact.

Folder layout (co-located with this file):

    stig_remediation_tool.html      UI rendered for GET /
    f5_client.py                    live appliance client
    live_evaluator.py               STIG evaluator + build_context
    data/
        ControlCatalog.json
        LiveControlOutcomeMatrix.json
        ExternalEvidencePackages.json
    stig_config_lookup/
        host_list.csv               hosts shown in the login dropdown
        stig_list.csv               control inventory surfaced in the sidebar
    bundles/<host_ip>/<vid>/<ts>.json
    bundles/<host_ip>/<vid>/latest.json
    snippets/<vid>.conf
    sessions/<token>.json
    validate_all/<host_ip>/<ts>.json
    live_state/                     transient snapshots + content-addressed blobs

Run:

    cd factory_exports/stig_expert_critic
    python web_app.py
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
import os
import secrets
import socket
import sys
import threading
import traceback
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

FACTORY_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(FACTORY_ROOT))

from f5_client import F5Client  # type: ignore  # noqa: E402
from live_evaluator import (  # type: ignore  # noqa: E402
    build_context,
    evaluate_control,
    load_external_packages,
)

# ---------------------------------------------------------------------------
# Paths & configuration (all rooted at this folder so the factory is portable)
# ---------------------------------------------------------------------------

TEMPLATE_PATH = FACTORY_ROOT / "stig_remediation_tool.html"
DATA_DIR = FACTORY_ROOT / "data"
CATALOG_PATH = DATA_DIR / "ControlCatalog.json"
OUTCOME_PATH = DATA_DIR / "LiveControlOutcomeMatrix.json"
EXTERNAL_PATH = DATA_DIR / "ExternalEvidencePackages.json"

HOST_CSV = FACTORY_ROOT / "stig_config_lookup" / "host_list.csv"
STIG_CSV = FACTORY_ROOT / "stig_config_lookup" / "stig_list.csv"
BUNDLES_ROOT = FACTORY_ROOT / "bundles"
SNIPPETS_ROOT = FACTORY_ROOT / "snippets"
SESSIONS_ROOT = FACTORY_ROOT / "sessions"
VALIDATE_ALL_ROOT = FACTORY_ROOT / "validate_all"
RESIDUALS_ROOT = FACTORY_ROOT / "residuals"

for _d in (
    BUNDLES_ROOT,
    SNIPPETS_ROOT,
    SESSIONS_ROOT,
    VALIDATE_ALL_ROOT,
    RESIDUALS_ROOT,
    FACTORY_ROOT / "stig_config_lookup",
):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Status mapping (disposition -> template status conventions)
# ---------------------------------------------------------------------------

_DISPOSITION_TO_STATUS = {
    "pass": ("NOT_A_FINDING", "not_a_finding"),
    "not-applicable": ("NOT_A_FINDING", "not_a_finding"),
    "fail": ("OPEN", "open"),
    "blocked-external": ("UNKNOWN", "unknown"),
}

_DISPOSITION_TO_STAGE = {
    "pass": ("stable", ""),
    "not-applicable": ("stable", ""),
    "fail": ("provisional", "local_evidence_gap"),
    "blocked-external": ("provisional", "external_evidence_gap"),
}

# ---------------------------------------------------------------------------
# Handler-family -> remediation guidance surfaced in the UI
# ---------------------------------------------------------------------------

DOD_BANNER = (
    "You are accessing a U.S. Government (USG) Information System (IS) that is "
    "provided for USG-authorized use only. By using this IS (which includes any "
    "device attached to this IS), you consent to the following conditions..."
)

FAMILY_GUIDANCE: Dict[str, Dict[str, Any]] = {
    "banner": {
        "tmsh_commands": [
            "list sys global-settings login-banner-text",
            "list sys httpd auth-pam-dashboard-timeout",
        ],
        "rest_endpoints": ["/mgmt/tm/sys/global-settings"],
        "fix_tmsh": (
            "tmsh modify sys global-settings gui-setup disabled "
            f"login-banner-text \"{DOD_BANNER}\"; tmsh save sys config"
        ),
        "fix_rest": (
            "PATCH /mgmt/tm/sys/global-settings "
            "{\"loginBannerText\": \"<DoD banner>\", \"guiSetup\": \"disabled\"}"
        ),
        "remediation_note": "Install the approved DoD banner in Security Policy.",
    },
    "sshd": {
        "tmsh_commands": ["list sys sshd all-properties"],
        "rest_endpoints": ["/mgmt/tm/sys/sshd"],
        "fix_tmsh": "tmsh modify sys sshd inactivity-timeout 600 login no; tmsh save sys config",
        "fix_rest": (
            "PATCH /mgmt/tm/sys/sshd "
            "{\"inactivityTimeout\": 600, \"login\": \"no\"}"
        ),
        "remediation_note": "Disable SSH root logins and enforce idle-session timeout.",
    },
    "password_policy": {
        "tmsh_commands": ["list auth password-policy all-properties"],
        "rest_endpoints": ["/mgmt/tm/auth/password-policy"],
        "fix_tmsh": (
            "tmsh modify auth password-policy policy-enforcement enabled "
            "max-login-failures 3 lockout-duration 900 minimum-length 15 "
            "required-uppercase 1 required-lowercase 1 required-numeric 1 "
            "required-special 1 password-memory 5 expiration-warning 14; "
            "tmsh save sys config"
        ),
        "fix_rest": (
            "PATCH /mgmt/tm/auth/password-policy "
            "{\"policyEnforcement\":\"enabled\",\"maxLoginFailures\":3,"
            "\"lockoutDuration\":900,\"minimumLength\":15}"
        ),
        "remediation_note": (
            "Enforce the DoD password policy (length, complexity, reuse, "
            "max failures, lockout)."
        ),
    },
    "ntp": {
        "tmsh_commands": ["list sys ntp"],
        "rest_endpoints": ["/mgmt/tm/sys/ntp"],
        "fix_tmsh": (
            "tmsh modify sys ntp servers add { <approved_ntp1> <approved_ntp2> }; "
            "tmsh save sys config"
        ),
        "fix_rest": (
            "PATCH /mgmt/tm/sys/ntp "
            "{\"servers\": [\"<approved_ntp1>\", \"<approved_ntp2>\"]}"
        ),
        "remediation_note": "Point NTP at two organizationally approved time sources.",
    },
    "logging": {
        "tmsh_commands": [
            "list sys syslog all-properties",
            "list sys snmp all-properties",
        ],
        "rest_endpoints": [
            "/mgmt/tm/sys/syslog",
            "/mgmt/tm/sys/snmp",
        ],
        "fix_tmsh": (
            "[Manual] tmsh modify sys syslog remote-servers replace-all-with "
            "{ stig_syslog1 { host <siem1> } stig_syslog2 { host <siem2> } }; "
            "tmsh save sys config"
        ),
        "fix_rest": "[Manual] PATCH /mgmt/tm/sys/syslog with org-approved remote SIEM servers.",
        "remediation_note": "Forward audit events to at least two approved syslog receivers.",
    },
    "apm_access": {
        "tmsh_commands": [
            "list apm profile access all-properties",
            "list apm policy access-policy all-properties",
        ],
        "rest_endpoints": [
            "/mgmt/tm/apm/profile/access",
            "/mgmt/tm/apm/policy/access-policy",
        ],
        "fix_tmsh": "[Manual] Review APM access profile / policy and apply DoD-approved controls.",
        "fix_rest": "[Manual] PATCH APM objects via Policy Editor or iControl-REST.",
        "remediation_note": "APM changes require policy author review before applying.",
    },
    "asm_policy": {
        "tmsh_commands": ["list asm policy all-properties"],
        "rest_endpoints": ["/mgmt/tm/asm/policies", "/mgmt/tm/ltm/virtual"],
        "fix_tmsh": "[Manual] Attach an active, enforced ASM policy to the STIG-scoped virtual server.",
        "fix_rest": "[Manual] PATCH /mgmt/tm/asm/policies/<id> {\"active\":true,\"enforcementMode\":\"blocking\"}",
        "remediation_note": "ASM remediation requires learning/tuning; do not auto-apply.",
    },
    "afm_firewall": {
        "tmsh_commands": ["list security firewall policy all-properties"],
        "rest_endpoints": ["/mgmt/tm/security/firewall/policy"],
        "fix_tmsh": "[Manual] Enforce an AFM policy on the scoped virtual with approved rules.",
        "fix_rest": "[Manual] PATCH /mgmt/tm/ltm/virtual/<name> to attach an enforced AFM policy.",
        "remediation_note": "AFM rule changes must go through change management.",
    },
    "ltm_virtual_services": {
        "tmsh_commands": ["list ltm virtual all-properties"],
        "rest_endpoints": ["/mgmt/tm/ltm/virtual"],
        "fix_tmsh": "[Manual] Disable or delete only the exact virtual servers that violate the local PPSM/SSP allowlist.",
        "fix_rest": "[Manual] DELETE /mgmt/tm/ltm/virtual/<name> only after local authorization review.",
        "remediation_note": "Requires local PPSM CAL / SSP authorization evidence; raw service inventory stays on target.",
    },
    "ltm_virtual_ssl": {
        "tmsh_commands": [
            "list ltm profile client-ssl all-properties",
            "list ltm virtual all-properties",
        ],
        "rest_endpoints": [
            "/mgmt/tm/ltm/profile/client-ssl",
            "/mgmt/tm/ltm/virtual",
        ],
        "fix_tmsh": "[Manual] Bind a FIPS-validated client-ssl profile (TLS 1.2+) to the virtual.",
        "fix_rest": "[Manual] PATCH /mgmt/tm/ltm/virtual/<name> to set a FIPS client-ssl profile.",
        "remediation_note": "Requires signed FIPS-validated cert and approved cipher list.",
    },
    "backup": {
        "tmsh_commands": ["list sys ucs"],
        "rest_endpoints": ["/mgmt/tm/sys/ucs"],
        "fix_tmsh": "tmsh save sys ucs /var/local/ucs/stig_backup.ucs passphrase <org_phrase>",
        "fix_rest": "[Manual] POST /mgmt/tm/sys/ucs with organization-approved passphrase.",
        "remediation_note": "Periodic UCS archives must be transferred off-device.",
    },
    "manual_or_generic": {
        "tmsh_commands": [],
        "rest_endpoints": [],
        "fix_tmsh": "NA",
        "fix_rest": "NA",
        "remediation_note": "Generic or policy-level control -- see STIG check text.",
    },
}


def family_guidance(family: str) -> Dict[str, Any]:
    return FAMILY_GUIDANCE.get(family, FAMILY_GUIDANCE["manual_or_generic"])


FAMILY_EVIDENCE_KEYS = {
    "banner": ["tmsh_sys_global_settings"],
    "sshd": ["sys_sshd"],
    "password_policy": ["tmsh_auth_password_policy"],
    "ntp": ["tmsh_sys_ntp"],
    "logging": ["tmsh_sys_syslog", "bash_log_storage_capacity"],
    "apm_access": [
        "tmsh_apm_profile_access",
        "tmsh_apm_policy_access_policy",
        "tmsh_apm_log_setting",
    ],
    "asm_policy": ["tmsh_asm_policy", "tmsh_ltm_virtual"],
    "afm_firewall": ["tmsh_security_firewall_policy"],
    "ltm_virtual_services": ["tmsh_ltm_virtual"],
    "ltm_virtual_ssl": ["tmsh_ltm_profile_client_ssl", "tmsh_ltm_virtual"],
    "backup": ["tmsh_sys_ucs"],
    "manual_or_generic": ["sys_provision"],
}

# ---------------------------------------------------------------------------
# Host & contract synthesis
# ---------------------------------------------------------------------------


def load_hosts() -> List[Dict[str, str]]:
    if not HOST_CSV.exists():
        return []
    hosts: List[Dict[str, str]] = []
    with HOST_CSV.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ip = (row.get("ip_address") or "").strip()
            name = (row.get("hostname") or "").strip()
            if not ip:
                continue
            label = f"{name} ({ip})" if name else ip
            hosts.append({"host": ip, "label": label, "hostname": name})
    return hosts


def _load_json(path: Path) -> Optional[Any]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_outcome_index() -> Dict[str, Dict[str, Any]]:
    doc = _load_json(OUTCOME_PATH) or {}
    out: Dict[str, Dict[str, Any]] = {}
    for row in doc.get("outcomes", []) or []:
        vid = row.get("vuln_id")
        if vid:
            out[vid] = row
    return out


def load_external_index() -> Dict[str, Dict[str, Any]]:
    doc = _load_json(EXTERNAL_PATH) or {}
    out: Dict[str, Dict[str, Any]] = {}
    for pkg in doc.get("packages", []) or []:
        for vid in pkg.get("controls", []) or []:
            out[vid] = pkg
    return out


def build_contracts() -> List[Dict[str, Any]]:
    catalog = _load_json(CATALOG_PATH) or {}
    outcomes = load_outcome_index()
    externals = load_external_index()
    contracts: List[Dict[str, Any]] = []

    for control in catalog.get("controls", []) or []:
        vid = control["vuln_id"]
        family = control.get("handler_family", "manual_or_generic")
        guidance = family_guidance(family)

        outcome = outcomes.get(vid) or {}
        disposition = outcome.get("disposition") or "unknown"
        rationale = outcome.get("rationale") or control.get("applicability_clause", "")

        uc_status, lc_status = _DISPOSITION_TO_STATUS.get(disposition, ("UNKNOWN", "unknown"))
        stage, blocked_by = _DISPOSITION_TO_STAGE.get(disposition, ("provisional", ""))

        ext_pkg = externals.get(vid)
        if ext_pkg and disposition == "blocked-external":
            blocked_by = f"external:{ext_pkg.get('package_id', 'unknown')}"

        rest_eps = guidance["rest_endpoints"] or control.get("candidate_read_paths", []) or []
        tmsh_cmds = guidance["tmsh_commands"]

        criteria = {
            "not_a_finding": rationale or "disposition == pass",
            "open": "disposition == fail",
            "applicability": control.get("applicability_clause", ""),
            "evidence_kind": control.get("evidence_kind", ""),
            "handler_family": family,
        }

        evidence_required = outcome.get("evidence") or FAMILY_EVIDENCE_KEYS.get(
            family, ["sys_provision"]
        )

        remediation_method = "Manual"
        if guidance["fix_tmsh"] not in ("", "NA") and not guidance["fix_tmsh"].startswith("[Manual"):
            remediation_method = "TMSH / REST"
        elif guidance["fix_rest"] not in ("", "NA") and not guidance["fix_rest"].startswith("[Manual"):
            remediation_method = "REST"

        contracts.append({
            "vuln_id": vid,
            "rule_id": control.get("rule_id", ""),
            "check_id": control.get("check_id", ""),
            "fix_id": control.get("fix_id", ""),
            "title": control.get("title", ""),
            "severity": (control.get("severity") or "medium").lower(),
            "module": control.get("module", ""),
            "handler_family": family,
            "evidence_kind": control.get("evidence_kind", ""),
            "remediation_method": remediation_method,
            "evidence_required": list(evidence_required),
            "criteria": criteria,
            "tmsh_commands": list(tmsh_cmds),
            "rest_endpoints": list(rest_eps),
            "fix_tmsh": guidance["fix_tmsh"],
            "fix_rest": guidance["fix_rest"],
            "remediation_note": guidance["remediation_note"],
            "maturity_stage": stage,
            "maturity_status": lc_status,
            "blocked_by": blocked_by,
            "disposition": disposition,
            "rationale": rationale,
            "source_stig": control.get("source_stig", {}),
        })
    return contracts


# ---------------------------------------------------------------------------
# Session store (simple in-memory + on-disk audit)
# ---------------------------------------------------------------------------


@dataclass
class Session:
    token: str
    host: str
    user: str
    created: str
    client: F5Client
    ctx_lock: threading.Lock = field(default_factory=threading.Lock)
    ctx_cache: Optional[Dict[str, Any]] = None
    ctx_timestamp: Optional[str] = None


class SessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_token: Dict[str, Session] = {}

    def create(self, host: str, user: str, password: str) -> Session:
        client = F5Client(host=host, user=user, password=password)
        client.get("/mgmt/tm/sys/provision")
        token = secrets.token_urlsafe(24)
        sess = Session(
            token=token,
            host=host,
            user=user,
            created=utc_now_iso(),
            client=client,
        )
        with self._lock:
            self._by_token[token] = sess
        _write_json(SESSIONS_ROOT / f"{token}.json", {
            "token": token,
            "host": host,
            "user": user,
            "created": sess.created,
        })
        return sess

    def get(self, token: Optional[str]) -> Optional[Session]:
        if not token:
            return None
        with self._lock:
            return self._by_token.get(token)

    def drop(self, token: Optional[str]) -> None:
        if not token:
            return
        with self._lock:
            self._by_token.pop(token, None)
        try:
            (SESSIONS_ROOT / f"{token}.json").unlink()
        except FileNotFoundError:
            pass


SESSIONS = SessionStore()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return _dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def timestamp_slug() -> str:
    return _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


def _append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True) + "\n")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _factory_rel(path: Path) -> str:
    return str(path.relative_to(FACTORY_ROOT)).replace("\\", "/")


# ---------------------------------------------------------------------------
# Evaluator bridge: call live evaluator and shape for the template
# ---------------------------------------------------------------------------


def _get_or_build_ctx(session: Session) -> Dict[str, Any]:
    with session.ctx_lock:
        if session.ctx_cache is None:
            session.ctx_cache = build_context(session.client)
            session.ctx_timestamp = utc_now_iso()
        return session.ctx_cache


def _invalidate_ctx(session: Session) -> None:
    with session.ctx_lock:
        session.ctx_cache = None
        session.ctx_timestamp = None


def _find_control(vuln_id: str) -> Optional[Dict[str, Any]]:
    catalog = _load_json(CATALOG_PATH) or {}
    for control in catalog.get("controls", []) or []:
        if control.get("vuln_id") == vuln_id:
            return control
    return None


def _short(text: str, limit: int) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= limit:
        return t
    return t[:limit] + f" ... ({len(t) - limit} more chars)"


def _source_coordinate(source_key: str, ctx: Dict[str, Any]) -> str:
    """Return a reviewer-friendly coordinate for a snapshot source key.

    ``tmsh_sys_httpd`` -> ``tmsh:list sys httpd all-properties``
    ``sys_global_settings`` -> ``rest:/mgmt/tm/sys/global-settings``
    ``bash_*`` -> ``bash:<command>``
    ``external_evidence_packages`` -> ``repo-json:data/ExternalEvidencePackages.json``
    """
    if not source_key:
        return "appliance:unknown"
    snaps = (ctx or {}).get("snapshots") or {}
    meta = snaps.get(source_key)
    if meta:
        src = meta.get("source") or {}
        kind = src.get("kind")
        if kind == "tmsh":
            return f"tmsh:{src.get('command', source_key)}"
        if kind == "bash":
            return f"bash:{src.get('command', source_key)}"
        if kind == "rest":
            return f"rest:{src.get('path', source_key)}"
        if kind == "repo-json":
            return f"repo-json:{src.get('path', source_key)}"
    return f"appliance:{source_key}"


def _summary_for_evidence(
    ctx: Dict[str, Any],
    measurements: List[Dict[str, Any]] | None,
    fallback_keys: List[str] | None = None,
) -> Dict[str, Any]:
    """Summarise the snapshots this control actually relied on.

    We key the evidence panel on the distinct ``source`` fields emitted by the
    evaluator's measurement rows -- so reviewers see exactly the tmsh/REST
    endpoints the verdict was derived from, paired with a short text preview
    and a content-addressed blob fingerprint they can verify.
    """
    out: Dict[str, Any] = {}
    texts = ctx.get("texts") or {}
    snaps = ctx.get("snapshots") or {}

    keys: List[str] = []
    seen = set()
    for row in (measurements or []):
        src = row.get("source")
        if src and src not in seen:
            seen.add(src)
            keys.append(src)
    for k in (fallback_keys or []):
        if k not in seen:
            seen.add(k)
            keys.append(k)

    for key in keys:
        entry: Dict[str, Any] = {"source": key}
        # Map source key -> best text-hit in ctx.texts (naming convention:
        # tmsh_<name> -> texts["<name>"]) so we can show a short preview.
        preview_key = None
        if key.startswith("tmsh_"):
            preview_key = key[5:]
        elif key in texts:
            preview_key = key
        if preview_key and preview_key in texts:
            entry["preview"] = _short(texts[preview_key], 240)
        meta = snaps.get(key)
        if meta:
            entry["source_detail"] = meta.get("source") or {}
            entry["blob_sha256"] = (meta.get("blob_sha256") or "")[:16]
            entry["bytes"] = meta.get("bytes", 0)
        out[key] = entry
    return out


def _coerce_required_observed(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _stable_measurement_id(vuln_id: str, measurable: str, ordinal: int) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in measurable).strip("_")
    safe = safe[:80] or f"measurement_{ordinal}"
    return f"{vuln_id}:{safe}:{ordinal}"


def _comparison_expression(required: str, observed: str) -> str:
    return f"observed({observed}) satisfies required({required})"


def _comparison_rows(
    control: Dict[str, Any],
    outcome: Dict[str, Any],
    ctx: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Project the evaluator's measurement list into truth-table rows.

    Each measurement becomes a single row -- the atomic unit that a STIG
    reviewer critiques.  If an older bundle lacks measurements we synthesise
    a single generic row so the UI still renders something sensible.
    """
    vid = control["vuln_id"]
    disposition = outcome.get("disposition", "unknown")
    measurements = outcome.get("measurements") or []

    if measurements:
        rows: List[Dict[str, Any]] = []
        for idx, m in enumerate(measurements, start=1):
            measurable = m.get("measurable", "unknown_measurable")
            required = _coerce_required_observed(m.get("required", ""))
            observed = _coerce_required_observed(m.get("observed", ""))
            match = bool(m.get("match"))
            unresolved = bool(m.get("unresolved"))
            conf = 0.0 if unresolved else 1.0
            source_key = m.get("source") or ""
            carrier = _source_coordinate(source_key, ctx)
            pullback_id = _stable_measurement_id(vid, measurable, idx)
            row = {
                "pullback_id": pullback_id,
                "carrier_coordinate": carrier,
                "measurable": measurable,
                "lawful_property": required,
                "required": required,
                "observed": observed,
                "comparison_expression": _comparison_expression(required, observed),
                "match": match,
                "comparison_confidence": conf,
                "pullback_unmatched": unresolved,
                "reviewer_action": "external_evidence_required"
                if unresolved
                else "accept"
                if match
                else "remediate_or_document_exception",
                "source_key": source_key,
                "source_stig": control.get("source_stig", {}),
                "vuln_id": vid,
            }
            note = m.get("note")
            if note:
                row["note"] = note
            rows.append(row)
        return rows

    # -- Legacy fallback (bundles written before measurements existed) ------
    family = control.get("handler_family", "manual_or_generic")
    texts = ctx.get("texts") or {}
    measurable = f"{family}_state"
    fallback_source_key = (FAMILY_EVIDENCE_KEYS.get(family, []) or ["sys_provision"])[0]
    carrier = _source_coordinate(fallback_source_key, ctx)
    required_text = control.get("applicability_clause") or outcome.get("rationale") or ""
    observed_text = ""
    for k in FAMILY_EVIDENCE_KEYS.get(family, []):
        if k in texts and texts[k].strip():
            observed_text = _short(texts[k], 300)
            break
    if not observed_text:
        observed_text = _short(outcome.get("rationale", ""), 300)

    if disposition == "pass":
        match, conf = True, 1.0
    elif disposition == "fail":
        match, conf = False, 1.0
    elif disposition == "not-applicable":
        match, conf = True, 1.0
        required_text = "conditional N/A"
        observed_text = "conditional N/A satisfied"
    else:
        match, conf = False, 0.0

    return [{
        "pullback_id": _stable_measurement_id(vid, measurable, 1),
        "carrier_coordinate": carrier,
        "measurable": measurable,
        "lawful_property": measurable,
        "required": required_text or "any truthy",
        "observed": observed_text or "none observed",
        "comparison_expression": _comparison_expression(
            required_text or "any truthy",
            observed_text or "none observed",
        ),
        "match": match,
        "comparison_confidence": conf,
        "pullback_unmatched": disposition == "blocked-external",
        "reviewer_action": "accept"
        if match
        else "external_evidence_required"
        if disposition == "blocked-external"
        else "remediate_or_document_exception",
        "source_key": fallback_source_key,
        "source_stig": control.get("source_stig", {}),
        "vuln_id": vid,
    }]


def _pullback_df(
    control: Dict[str, Any],
    outcome: Dict[str, Any],
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Describe the STIG alignment diagram over this control's measurements.

    * source_a = observed appliance evidence (one element per measurement)
    * source_b = STIG-required predicates (one element per measurement)
    * codomain = shared measurable names (e.g. ``sys_httpd.max_clients``)
    * map_a/map_b = the projection of each side onto the measurable
    * match_rule = "observed value satisfies required predicate"

    Each fiber pair identifies a reviewer-critique-able triple
    (measurable, observed, required) keyed by the measurable name.
    """
    vid = control["vuln_id"]
    disposition = outcome.get("disposition", "unknown")
    match_count = sum(1 for r in rows if r.get("match") is True)
    mismatch_count = sum(
        1 for r in rows
        if r.get("match") is not True and float(r.get("comparison_confidence", 1)) > 0
    )
    unresolved = sum(1 for r in rows if float(r.get("comparison_confidence", 1)) == 0)

    def _fiber_pair(r: Dict[str, Any]) -> Dict[str, Any]:
        m = r.get("measurable", "?")
        obs = _short(str(r.get("observed", "")), 60)
        req = _short(str(r.get("required", "")), 60)
        match = r.get("match") is True
        unresolved_row = bool(r.get("pullback_unmatched"))
        if unresolved_row:
            cardinality = "unresolved"
        elif match:
            cardinality = "ok"
        else:
            cardinality = "mismatch"
        return {
            "pullback_id": r.get("pullback_id", ""),
            "shared_key": m,
            "left_id": f"observed[{m}] = {obs}",
            "right_id": f"required[{m}] {req}",
            "observed_value": r.get("observed", ""),
            "required_value": r.get("required", ""),
            "comparison_expression": r.get("comparison_expression", ""),
            "cardinality": cardinality,
            "source": r.get("carrier_coordinate", ""),
        }

    diagram = {
        "record_type": "diagram",
        "source_a": f"observed appliance evidence ({vid})",
        "source_a_count": len(rows),
        "source_b": f"STIG-required predicates ({vid})",
        "source_b_count": len(rows),
        "codomain": f"shared measurables ({vid})",
        "map_a": "appliance snapshot -> measurable value",
        "map_b": "STIG predicate -> measurable constraint",
        "match_rule": "observed value satisfies required predicate on the shared measurable",
        "match_count": match_count,
        "mismatch_count": mismatch_count,
        "unresolved_count": unresolved,
        "fiber_pairs": [_fiber_pair(r) for r in rows],
    }

    entries: List[Dict[str, Any]] = [diagram]

    if mismatch_count:
        entries.append({
            "record_type": "criticism",
            "severity": "error",
            "aspect": "mismatch",
            "finding": (
                f"{mismatch_count} measurement(s) observed on the appliance do not "
                f"satisfy the STIG predicate; see the truth table for exact values."
            ),
        })
    if unresolved:
        entries.append({
            "record_type": "criticism",
            "severity": "warning",
            "aspect": "unresolved",
            "finding": (
                f"{unresolved} measurement(s) cannot be closed by on-appliance evidence "
                f"alone; external attestation is required."
            ),
        })
    if disposition == "pass" and not mismatch_count and not unresolved:
        entries.append({
            "record_type": "criticism",
            "severity": "info",
            "aspect": "confirmation",
            "finding": "Every measured predicate is satisfied by observed appliance evidence.",
        })

    for r in rows:
        m = r.get("measurable", "?")
        if r.get("match") is True:
            rec_type = "match"
        elif r.get("pullback_unmatched"):
            rec_type = "unmatched_right"
        else:
            rec_type = "mismatch"
        entries.append({
            "record_type": rec_type,
            "pullback_id": r.get("pullback_id", ""),
            "shared_key": m,
            "left_id": f"observed[{m}] = {_short(str(r.get('observed', '')), 60)}",
            "right_id": f"required[{m}] {_short(str(r.get('required', '')), 60)}",
            "observed_value": r.get("observed", ""),
            "required_value": r.get("required", ""),
            "source": r.get("carrier_coordinate", ""),
            "comparison_expression": r.get("comparison_expression", ""),
        })

    return entries


def _proof_steps(
    control: Dict[str, Any],
    outcome: Dict[str, Any],
    rows: List[Dict[str, Any]],
    pullback_df: List[Dict[str, Any]],
    status_uc: str,
) -> List[Dict[str, Any]]:
    family = control.get("handler_family", "manual_or_generic")
    guidance = family_guidance(family)
    vid = control["vuln_id"]
    pass_count = sum(1 for r in rows if r.get("match") is True)
    fail_count = sum(1 for r in rows if r.get("match") is not True and float(r.get("comparison_confidence", 1)) > 0)
    unresolved_count = sum(1 for r in rows if float(r.get("comparison_confidence", 1)) == 0)

    diagram = next((p for p in pullback_df if p.get("record_type") == "diagram"), {})

    observed_sources: List[str] = []
    seen_sources = set()
    for r in rows:
        coord = r.get("carrier_coordinate") or ""
        if coord and coord not in seen_sources:
            seen_sources.add(coord)
            observed_sources.append(coord)
    if not observed_sources:
        observed_sources = guidance["rest_endpoints"] + guidance["tmsh_commands"]

    steps: List[Dict[str, Any]] = []
    steps.append({
        "step": "recipe",
        "title": f"{vid} - {family} evaluation recipe",
        "detail": (
            "Capture live evidence -> emit one measurement per STIG predicate -> "
            "pull back observed vs required on the shared measurable -> compare -> judge."
        ),
    })
    steps.append({
        "step": "observe",
        "title": f"Observe appliance state for {vid}",
        "detail": (
            f"Collected {len(observed_sources)} source snapshot(s) producing "
            f"{len(rows)} measurement(s)."
        ),
        "endpoints": observed_sources,
    })
    steps.append({
        "step": "pullback_diagram",
        "title": f"STIG alignment diagram - {vid}",
        "source_a": diagram.get("source_a"),
        "source_a_count": diagram.get("source_a_count"),
        "source_b": diagram.get("source_b"),
        "source_b_count": diagram.get("source_b_count"),
        "codomain": diagram.get("codomain"),
        "map_a": diagram.get("map_a"),
        "map_b": diagram.get("map_b"),
        "match_rule": diagram.get("match_rule"),
        "match_count": diagram.get("match_count", 0),
        "unmatched_left": 0,
        "unmatched_right": fail_count,
        "mismatch_count": fail_count,
        "unresolved_count": unresolved_count,
        "fiber_pairs": diagram.get("fiber_pairs", []),
        "missing_items": [
            r.get("measurable", "?") for r in rows
            if r.get("match") is not True and not r.get("pullback_unmatched")
        ],
        "waste_items": [
            r.get("measurable", "?") for r in rows if r.get("pullback_unmatched")
        ],
    })
    for criticism in (c for c in pullback_df if c.get("record_type") == "criticism"):
        steps.append({
            "step": "pullback_criticism",
            "title": f"Criticism - {criticism.get('aspect', '')}",
            "severity": criticism.get("severity", "info"),
            "aspect": criticism.get("aspect", ""),
            "detail": criticism.get("finding", ""),
        })
    for r in rows:
        conf = float(r.get("comparison_confidence", 1))
        if r.get("match") is True:
            verdict = "PASS"
        elif conf == 0:
            verdict = "UNRESOLVED"
        else:
            verdict = "FAIL"
        title_bits = [r.get("measurable", "?")]
        src = r.get("carrier_coordinate")
        if src:
            title_bits.append(src)
        steps.append({
            "step": "compare",
            "title": "Compare - " + " @ ".join(title_bits),
            "pullback_id": r.get("pullback_id", ""),
            "required": str(r.get("required", "")),
            "observed": str(r.get("observed", "")),
            "source": str(r.get("carrier_coordinate", "")),
            "comparison_expression": str(r.get("comparison_expression", "")),
            "verdict": verdict,
            "is_unmatched": r.get("pullback_unmatched", False),
        })
    steps.append({
        "step": "evidence_summary",
        "title": "Evidence tally",
        "pass_count": pass_count,
        "fail_count": fail_count,
        "unresolved_count": unresolved_count,
        "total_comparisons": len(rows),
    })

    naf_expr = str(control.get("applicability_clause") or "observed == required").strip() or "observed == required"
    steps.append({
        "step": "criteria",
        "title": "Judgment",
        "detail": outcome.get("rationale", ""),
        "status": status_uc,
        "naf_expression": naf_expr[:140],
        "naf_result": status_uc == "NOT_A_FINDING",
        "open_expression": "pullback mismatch OR unresolved expectation",
        "open_result": status_uc == "OPEN",
    })
    return steps


def _adjudication(
    control: Dict[str, Any],
    outcome: Dict[str, Any],
    rows: List[Dict[str, Any]],
    pullback_df: List[Dict[str, Any]],
    status_uc: str,
) -> Dict[str, Any]:
    family = control.get("handler_family", "manual_or_generic")
    guidance = family_guidance(family)
    compliant = status_uc == "NOT_A_FINDING"
    violations: List[str] = []
    if status_uc == "OPEN":
        violations.append(outcome.get("rationale") or "Appliance state does not satisfy the STIG predicate.")
    if status_uc == "UNKNOWN":
        violations.append(outcome.get("rationale") or "External evidence is required to close this control.")

    human = {
        "vuln_id": control["vuln_id"],
        "requirement": control.get("title", ""),
        "status": status_uc,
        "why": outcome.get("rationale", ""),
        "tmsh_remediation_command": guidance["fix_tmsh"],
        "rest_remediation_command": guidance["fix_rest"],
        "evidence_keys": FAMILY_EVIDENCE_KEYS.get(family, []),
        "comparison_summary": {
            "total": len(rows),
            "pass": sum(1 for r in rows if r.get("match") is True),
            "fail": sum(
                1
                for r in rows
                if r.get("match") is not True
                and float(r.get("comparison_confidence", 1)) > 0
            ),
            "unresolved": sum(
                1 for r in rows if float(r.get("comparison_confidence", 1)) == 0
            ),
        },
    }

    return {
        "compliant": compliant,
        "human_review_row": human,
        "violations": violations,
        "proof_steps": _proof_steps(control, outcome, rows, pullback_df, status_uc),
    }


def _bundle_dir_for(host: str, vid: str) -> Path:
    safe = host.replace(":", "_").replace("/", "_")
    d = BUNDLES_ROOT / safe / vid
    d.mkdir(parents=True, exist_ok=True)
    return d


def _persist_bundle(
    host: str,
    vid: str,
    data: Dict[str, Any],
    operation: str,
    bundle_source: str,
) -> Dict[str, Any]:
    ts = utc_now_iso()
    bundle = dict(data)
    bundle["bundle_metadata"] = {
        "operation": operation,
        "bundle_source": bundle_source,
        "bundle_timestamp": ts,
        "bundle_host_ip": host,
        "vuln_id": vid,
    }
    bundle["requested_host"] = host
    out_dir = _bundle_dir_for(host, vid)
    fname = timestamp_slug() + ".json"
    path = out_dir / fname
    bundle_rel = _factory_rel(path)
    bundle["bundle_dir"] = bundle_rel
    bundle["provenance"] = {
        "bundle_dir": bundle_rel,
        "bundle_timestamp": ts,
        "bundle_host_ip": host,
        "bundle_host_hostname": host,
        "bundle_operation": operation,
        "bundle_source": bundle_source,
        "bundle_is_synthetic": False,
        "host_match": True,
        "selection_note": f"Live {operation} against {host}.",
    }
    _write_json(path, bundle)
    _write_json(out_dir / "latest.json", bundle)
    return bundle


def _load_bundle(host: str, vid: str) -> Optional[Dict[str, Any]]:
    latest = _bundle_dir_for(host, vid) / "latest.json"
    if not latest.exists():
        return None
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_single_validation(
    session: Session,
    control: Dict[str, Any],
    ctx: Dict[str, Any],
) -> Dict[str, Any]:
    outcome = evaluate_control(control, ctx)
    family = control.get("handler_family", "manual_or_generic")
    status_uc, _ = _DISPOSITION_TO_STATUS.get(outcome["disposition"], ("UNKNOWN", "unknown"))

    rows = _comparison_rows(control, outcome, ctx)
    pb = _pullback_df(control, outcome, rows)
    adj = _adjudication(control, outcome, rows, pb, status_uc)
    evidence = _summary_for_evidence(
        ctx,
        outcome.get("measurements") or [],
        FAMILY_EVIDENCE_KEYS.get(family, []),
    )

    return {
        "ok": True,
        "vuln_id": control["vuln_id"],
        "source_stig": control.get("source_stig", {}),
        "status": status_uc,
        "disposition": outcome["disposition"],
        "evidence": evidence,
        "comparison_df": rows,
        "pullback_df": pb,
        "adjudication": adj,
        "rationale": outcome.get("rationale", ""),
        "ctx_timestamp": session.ctx_timestamp,
    }


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

COOKIE_NAME = "stig_factory_session"


def _read_body_json(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON body: {exc}") from exc


def _session_from_request(handler: BaseHTTPRequestHandler) -> Optional[Session]:
    raw = handler.headers.get("Cookie") or ""
    if not raw:
        return None
    jar = SimpleCookie()
    try:
        jar.load(raw)
    except Exception:
        return None
    morsel = jar.get(COOKIE_NAME)
    if not morsel:
        return None
    return SESSIONS.get(morsel.value)


class Handler(BaseHTTPRequestHandler):
    server_version = "STIGFactory/1.0"

    def _send_json(self, code: int, payload: Any, extra_headers: Optional[Dict[str, str]] = None) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, code: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys.stderr.write("[web_app] %s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        try:
            self._route_get()
        except Exception:
            self._handle_exception()

    def do_POST(self) -> None:  # noqa: N802
        try:
            self._route_post()
        except Exception:
            self._handle_exception()

    def _handle_exception(self) -> None:
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {
            "ok": False,
            "error": tb.splitlines()[-1] if tb else "internal error",
        })

    def _route_get(self) -> None:
        url = urlparse(self.path)
        path = url.path

        if path in ("/", "/index.html"):
            if not TEMPLATE_PATH.exists():
                self._send_text(HTTPStatus.NOT_FOUND, "template missing")
                return
            self._send_text(
                HTTPStatus.OK,
                TEMPLATE_PATH.read_text(encoding="utf-8"),
                content_type="text/html; charset=utf-8",
            )
            return

        if path == "/api/hosts":
            self._send_json(HTTPStatus.OK, load_hosts())
            return

        if path == "/api/contracts":
            self._send_json(HTTPStatus.OK, build_contracts())
            return

        if path.startswith("/api/hydrate/"):
            vid = path[len("/api/hydrate/"):]
            query = parse_qs(url.query or "")
            host = (query.get("host", [""])[0]) or ""
            if not host or not vid:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "host and vuln_id required"})
                return
            bundle = _load_bundle(host, vid)
            if not bundle:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "no persisted bundle"})
                return
            bundle["requested_host"] = host
            self._send_json(HTTPStatus.OK, bundle)
            return

        if path.startswith("/api/stig/read/"):
            vid = path[len("/api/stig/read/"):]
            snippet = SNIPPETS_ROOT / f"{vid}.conf"
            if snippet.exists():
                self._send_json(HTTPStatus.OK, {"ok": True, "content": snippet.read_text(encoding="utf-8")})
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "no snippet"})
            return

        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True, "ts": utc_now_iso()})
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"no route for GET {path}"})

    def _route_post(self) -> None:
        url = urlparse(self.path)
        path = url.path

        if path == "/api/login":
            self._handle_login()
            return
        if path == "/api/logout":
            self._handle_logout()
            return
        if path == "/api/validate":
            self._handle_validate()
            return
        if path == "/api/validate/all":
            self._handle_validate_all()
            return
        if path == "/api/remediate/tmsh":
            self._handle_remediate("tmsh")
            return
        if path == "/api/remediate/rest":
            self._handle_remediate("rest")
            return
        if path == "/api/tmsh-query":
            self._handle_tmsh_query()
            return
        if path == "/api/rest-query":
            self._handle_rest_query()
            return
        if path == "/api/verify":
            self._handle_verify()
            return
        if path == "/api/merge":
            self._handle_merge()
            return
        if path == "/api/save":
            self._handle_save()
            return
        if path == "/api/residuals/capture":
            self._handle_residual_capture()
            return
        if path.startswith("/api/stig/save/"):
            vid = path[len("/api/stig/save/"):]
            self._handle_stig_save(vid)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": f"no route for POST {path}"})

    def _handle_login(self) -> None:
        body = _read_body_json(self)
        host = (body.get("host") or "").strip()
        user = (body.get("username") or "").strip()
        password = body.get("password") or ""
        if not host or not user or not password:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "host, username, password required"})
            return
        try:
            session = SESSIONS.create(host, user, password)
        except Exception as exc:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": str(exc)})
            return

        cookie = SimpleCookie()
        cookie[COOKIE_NAME] = session.token
        cookie[COOKIE_NAME]["path"] = "/"
        cookie[COOKIE_NAME]["httponly"] = True
        cookie[COOKIE_NAME]["samesite"] = "Lax"
        self._send_json(
            HTTPStatus.OK,
            {"ok": True, "host": host, "user": user, "created": session.created},
            extra_headers={"Set-Cookie": cookie.output(header="").strip()},
        )

    def _handle_logout(self) -> None:
        session = _session_from_request(self)
        token = session.token if session else None
        SESSIONS.drop(token)
        expired = SimpleCookie()
        expired[COOKIE_NAME] = ""
        expired[COOKIE_NAME]["path"] = "/"
        expired[COOKIE_NAME]["max-age"] = 0
        self._send_json(HTTPStatus.OK, {"ok": True},
                        extra_headers={"Set-Cookie": expired.output(header="").strip()})

    def _require_session(self) -> Optional[Session]:
        session = _session_from_request(self)
        if session is None:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"ok": False, "error": "not connected"})
            return None
        return session

    def _handle_validate(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        vid = (body.get("vuln_id") or "").strip()
        control = _find_control(vid) if vid else None
        if not control:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unknown vuln_id"})
            return

        _invalidate_ctx(session)
        ctx = _get_or_build_ctx(session)
        result = run_single_validation(session, control, ctx)
        bundle = _persist_bundle(session.host, vid, result, "validate", "web_app")
        self._send_json(HTTPStatus.OK, bundle)

    def _handle_validate_all(self) -> None:
        session = self._require_session()
        if not session:
            return
        _invalidate_ctx(session)
        ctx = _get_or_build_ctx(session)
        catalog = _load_json(CATALOG_PATH) or {}
        controls = catalog.get("controls", []) or []

        results: List[Dict[str, Any]] = []
        summary: Dict[str, int] = {}
        for control in controls:
            try:
                res = run_single_validation(session, control, ctx)
            except Exception as exc:
                res = {
                    "ok": False,
                    "vuln_id": control["vuln_id"],
                    "status": "ERROR",
                    "error": str(exc),
                }
            bundle = _persist_bundle(session.host, control["vuln_id"], res, "validate_all", "web_app")
            results.append({
                "vuln_id": control["vuln_id"],
                "status": bundle.get("status"),
                "disposition": bundle.get("disposition"),
                "bundle_dir": bundle.get("bundle_dir"),
            })
            key = bundle.get("disposition") or "error"
            summary[key] = summary.get(key, 0) + 1

        run_doc = {
            "record_kind": "ValidateAllRun",
            "host": session.host,
            "ts": utc_now_iso(),
            "summary": dict(sorted(summary.items())),
            "results": results,
        }
        _write_json(VALIDATE_ALL_ROOT / session.host / (timestamp_slug() + ".json"), run_doc)
        self._send_json(HTTPStatus.OK, run_doc)

    def _handle_remediate(self, kind: str) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        vid = (body.get("vuln_id") or "").strip()
        if not body.get("confirm_execution"):
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "confirm_execution required"})
            return
        control = _find_control(vid) if vid else None
        if not control:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "unknown vuln_id"})
            return

        guidance = family_guidance(control.get("handler_family", "manual_or_generic"))
        command = guidance["fix_tmsh"] if kind == "tmsh" else guidance["fix_rest"]
        if not command or command == "NA" or command.startswith("[Manual"):
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": f"no automated {kind} remediation is available for {vid} -- manual steps required.",
            })
            return

        try:
            if kind == "tmsh":
                mutation_output: Any = session.client.run_bash(command)
            else:
                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "vuln_id": vid,
                    "advisory_only": True,
                    "message": (
                        "REST remediation is advisory-only in this exported UI. "
                        "Review the command, then apply through change control or Config Merge."
                    ),
                    "command": command,
                })
                return
        except Exception as exc:
            self._send_json(HTTPStatus.OK, {
                "ok": False,
                "vuln_id": vid,
                "error": f"{kind} remediation failed: {exc}",
                "command": command,
            })
            return

        _invalidate_ctx(session)
        ctx = _get_or_build_ctx(session)
        result = run_single_validation(session, control, ctx)
        result["mutation"] = mutation_output
        result["remediation"] = {"kind": kind, "command": command}
        bundle = _persist_bundle(session.host, vid, result, f"remediate_{kind}", "web_app")
        self._send_json(HTTPStatus.OK, bundle)

    def _handle_tmsh_query(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        command = (body.get("command") or "").strip()
        if not command:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "command required"})
            return
        try:
            out = session.client.run_tmsh(command)
        except Exception as exc:
            self._send_json(HTTPStatus.OK, {"ok": False, "error": str(exc), "command": command})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "command": command, "output": out})

    def _handle_rest_query(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        endpoint = (body.get("endpoint") or "").strip()
        if not endpoint or not endpoint.startswith("/"):
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "endpoint must start with '/' (e.g. /mgmt/tm/sys/httpd)",
            })
            return
        try:
            payload = session.client.get(endpoint)
        except Exception as exc:
            self._send_json(HTTPStatus.OK, {"ok": False, "error": str(exc), "endpoint": endpoint})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "endpoint": endpoint, "result": payload})

    def _run_merge_command(self, session: Session, config_text: str, verify: bool) -> Tuple[bool, str, str]:
        if not config_text.strip():
            return False, "configuration is empty", ""
        remote = f"/var/tmp/stig_factory_{uuid.uuid4().hex}.conf"
        encoded = config_text.replace("'", "'\"'\"'")
        write_cmd = f"printf %s '{encoded}' > {remote}"
        session.client.run_bash(write_cmd)
        verb = "verify" if verify else "merge"
        try:
            out = session.client.run_bash(f"tmsh load sys config {verb} file {remote}")
            ok = True
            err = ""
        except Exception as exc:
            out = ""
            err = str(exc)
            ok = False
        finally:
            try:
                session.client.run_bash(f"rm -f {remote}")
            except Exception:  # noqa: BLE001
                pass
        return ok, out, err

    def _handle_verify(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        ok, out, err = self._run_merge_command(session, body.get("config") or "", verify=True)
        self._send_json(HTTPStatus.OK, {
            "ok": ok,
            "message": "Verification passed -- merge available." if ok else "Verification failed.",
            "output": out or err,
            "error": err if not ok else "",
        })

    def _handle_merge(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        ok, out, err = self._run_merge_command(session, body.get("config") or "", verify=False)
        self._send_json(HTTPStatus.OK, {
            "ok": ok,
            "message": "Configuration merged into running config." if ok else "Merge failed.",
            "output": out or err,
            "error": err if not ok else "",
        })

    def _handle_save(self) -> None:
        session = self._require_session()
        if not session:
            return
        try:
            out = session.client.run_tmsh("save sys config")
            self._send_json(HTTPStatus.OK, {"ok": True, "message": "Running config saved.", "output": out})
        except Exception as exc:
            self._send_json(HTTPStatus.OK, {"ok": False, "error": str(exc), "message": "Save failed."})

    def _handle_residual_capture(self) -> None:
        session = self._require_session()
        if not session:
            return
        body = _read_body_json(self)
        vid = (body.get("vuln_id") or "").strip()
        residuals = body.get("residuals") or []
        if not vid or not isinstance(residuals, list):
            self._send_json(HTTPStatus.BAD_REQUEST, {
                "ok": False,
                "error": "vuln_id and residuals[] required",
            })
            return

        safe_host = session.host.replace(":", "_").replace("/", "_")
        path = RESIDUALS_ROOT / safe_host / vid / "residuals.jsonl"
        captured = 0
        captured_ids: List[str] = []
        for residual in residuals:
            if not isinstance(residual, dict):
                continue
            pullback_id = str(residual.get("pullback_id") or "")
            if not pullback_id:
                continue
            record = {
                "record_kind": "LocalResidualPullbackRecord",
                "residual_id": f"residual-{uuid.uuid4().hex}",
                "created": utc_now_iso(),
                "host": session.host,
                "user": session.user,
                "vuln_id": vid,
                "pullback_id": pullback_id,
                "measurable": residual.get("measurable", ""),
                "required": residual.get("required", ""),
                "observed": residual.get("observed", ""),
                "source": residual.get("source", ""),
                "comparison_expression": residual.get("comparison_expression", ""),
                "status": residual.get("status", "mismatch"),
                "reviewer_action": residual.get("reviewer_action", ""),
                "suggested_command": residual.get("suggested_command", ""),
                "bundle_dir": residual.get("bundle_dir", ""),
                "local_only": True,
                "export_policy": "raw_values_must_not_leave_target_environment",
                "state": "captured",
            }
            _append_jsonl(path, record)
            captured += 1
            captured_ids.append(record["residual_id"])

        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "captured": captured,
            "residual_ids": captured_ids,
            "path": _factory_rel(path),
            "local_only": True,
        })

    def _handle_stig_save(self, vid: str) -> None:
        body = _read_body_json(self)
        content = body.get("content") or ""
        if not vid or not content.strip():
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "vuln_id and content required"})
            return
        target = SNIPPETS_ROOT / f"{vid}.conf"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._send_json(HTTPStatus.OK, {
            "ok": True,
            "message": f"Saved snippet for {vid}.",
            "path": _factory_rel(target),
            "sha256": sha256_hex(content),
        })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> int:
    port = int(os.environ.get("STIG_FACTORY_PORT", "8080"))
    bind = os.environ.get("STIG_FACTORY_BIND", "127.0.0.1")
    server = ThreadingHTTPServer((bind, port), Handler)
    actual_host, actual_port = server.server_address[:2]
    display_hosts = [actual_host]
    if actual_host in ("", "0.0.0.0", "::"):
        display_hosts = ["127.0.0.1"]
        try:
            display_hosts.append(socket.gethostname())
        except OSError:
            pass
    print("[web_app] STIG expert-critic factory is listening.", flush=True)
    for host in dict.fromkeys(display_hosts):
        print(f"[web_app] Open: http://{host}:{actual_port}", flush=True)
    print(f"[web_app] bind address -> {actual_host}:{actual_port}", flush=True)
    print(f"[web_app] factory root -> {FACTORY_ROOT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[web_app] shutting down")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

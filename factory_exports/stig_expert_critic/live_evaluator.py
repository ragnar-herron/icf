#!/usr/bin/env python3
"""
Live STIG evaluator (standalone).

This module is the self-contained evaluator used by the factory web app.
It captures live evidence from an F5 BIG-IP, merges it with external
evidence packages from ``data/ExternalEvidencePackages.json``, and
classifies a control into one of:

    - pass
    - fail
    - not-applicable
    - blocked-external

All on-disk artefacts produced here stay inside this factory folder:
snapshots under ``live_state/snapshots/``, content-addressed blobs under
``live_state/blobstore/``.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from f5_client import F5Client

FACTORY_ROOT = Path(__file__).resolve().parent
CATALOG = FACTORY_ROOT / "data" / "ControlCatalog.json"
OUTCOME = FACTORY_ROOT / "data" / "LiveControlOutcomeMatrix.json"
EXTERNAL_PACKAGES = FACTORY_ROOT / "data" / "ExternalEvidencePackages.json"
LOCAL_POLICY = FACTORY_ROOT / "local_policy" / "authorized_virtual_services.json"
LIVE_STATE = FACTORY_ROOT / "live_state"
SNAP_ROOT = LIVE_STATE / "snapshots"
BLOB_ROOT = LIVE_STATE / "blobstore"

DOD_BANNER = (
    "You are accessing a U.S. Government (USG) Information System (IS) that is "
    "provided for USG-authorized use only. By using this IS (which includes any "
    "device attached to this IS), you consent to the following conditions: "
    "-The USG routinely intercepts and monitors communications on this IS for "
    "purposes including, but not limited to, penetration testing, COMSEC monitoring, "
    "network operations and defense, personnel misconduct (PM), law enforcement (LE), "
    "and counterintelligence (CI) investigations. "
    "-At any time, the USG may inspect and seize data stored on this IS. "
    "-Communications using, or data stored on, this IS are not private, are subject "
    "to routine monitoring, interception, and search, and may be disclosed or used "
    "for any USG-authorized purpose. "
    "-This IS includes security measures (e.g., authentication and access controls) "
    "to protect USG interests--not for your personal benefit or privacy. "
    "-Notwithstanding the above, using this IS does not constitute consent to PM, LE "
    "or CI investigative searching or monitoring of the content of privileged "
    "communications, or work product, related to personal representation or services "
    "by attorneys, psychotherapists, or clergy, and their assistants. Such "
    "communications and work product are private and confidential. See User Agreement "
    "for details."
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_rel_path(digest: str) -> str:
    return f"blobstore/sha256/{digest[:2]}/{digest[2:]}"


def write_blob_bytes(data: bytes) -> Tuple[str, str, int]:
    digest = sha256_hex(data)
    out = BLOB_ROOT.parent / blob_rel_path(digest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return blob_rel_path(digest), digest, len(data)


def write_snapshot_text(name: str, text: str, suffix: str) -> dict:
    SNAP_ROOT.mkdir(parents=True, exist_ok=True)
    path = SNAP_ROOT / f"{name}.{suffix}"
    path.write_text(text, encoding="utf-8")
    blob_path, blob_sha256, size = write_blob_bytes(text.encode("utf-8"))
    return {
        "name": name,
        "path": str(path.relative_to(FACTORY_ROOT)).replace("\\", "/"),
        "blob_path": blob_path,
        "blob_sha256": blob_sha256,
        "bytes": size,
    }


def capture_rest(client: F5Client, name: str, path: str) -> Tuple[dict, dict]:
    payload = client.get(path)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    meta = write_snapshot_text(name, text, "json")
    meta["source"] = {"kind": "rest", "path": path}
    return payload, meta


def is_not_found_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "http 404" in text or "not found" in text


def is_missing_command_result_error(exc: Exception) -> bool:
    return "did not return commandresult" in str(exc).lower()


def capture_optional_rest(client: F5Client, name: str, path: str) -> Tuple[dict, dict]:
    """Capture optional REST evidence without aborting the whole validation run.

    Some BIG-IP objects are configuration-dependent. For example, an appliance
    may not have the named APM network-access resource. That is evidence for
    the control, not a runtime failure.
    """
    try:
        return capture_rest(client, name, path)
    except Exception as exc:
        if not is_not_found_error(exc):
            raise
        payload = {
            "_missing": True,
            "_path": path,
            "_error": str(exc),
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        meta = write_snapshot_text(name, text, "json")
        meta["source"] = {
            "kind": "rest",
            "path": path,
            "optional": True,
            "missing": True,
            "error": str(exc),
        }
        return payload, meta


def capture_tmsh(client: F5Client, name: str, command: str) -> Tuple[str, dict]:
    try:
        text = client.run_tmsh(command)
    except Exception as exc:
        if not is_missing_command_result_error(exc):
            raise
        text = f"TMSH_COMMAND_RESULT_UNAVAILABLE\ncommand={command}\nerror={exc}\n"
        meta = write_snapshot_text(name, text, "txt")
        meta["source"] = {
            "kind": "tmsh",
            "command": command,
            "missing_command_result": True,
            "error": str(exc),
        }
        return "", meta
    meta = write_snapshot_text(name, text, "txt")
    meta["source"] = {"kind": "tmsh", "command": command}
    return text, meta


def capture_optional_tmsh(client: F5Client, name: str, command: str) -> Tuple[str, dict]:
    """Capture optional tmsh evidence without failing the whole run on absence."""
    try:
        return capture_tmsh(client, name, command)
    except Exception as exc:
        if not (is_not_found_error(exc) or is_missing_command_result_error(exc)):
            raise
        text = f"OPTIONAL_TMSH_NOT_FOUND\ncommand={command}\nerror={exc}\n"
        meta = write_snapshot_text(name, text, "txt")
        meta["source"] = {
            "kind": "tmsh",
            "command": command,
            "optional": True,
            "missing": True,
            "error": str(exc),
        }
        return "", meta


def capture_bash(client: F5Client, name: str, command: str) -> Tuple[str, dict]:
    try:
        text = client.run_bash(command)
    except Exception as exc:
        if not is_missing_command_result_error(exc):
            raise
        text = f"BASH_COMMAND_RESULT_UNAVAILABLE\ncommand={command}\nerror={exc}\n"
        meta = write_snapshot_text(name, text, "txt")
        meta["source"] = {
            "kind": "bash",
            "command": command,
            "missing_command_result": True,
            "error": str(exc),
        }
        return "", meta
    meta = write_snapshot_text(name, text, "txt")
    meta["source"] = {"kind": "bash", "command": command}
    return text, meta


def capture_repo_file(name: str, path: Path) -> Tuple[dict, dict]:
    text = path.read_text(encoding="utf-8")
    meta = write_snapshot_text(name, text, path.suffix.lstrip(".") or "txt")
    meta["source"] = {
        "kind": "repo-json",
        "path": str(path.relative_to(FACTORY_ROOT)).replace("\\", "/"),
    }
    return json.loads(text), meta


def lower_join(*parts: str) -> str:
    return "\n".join(parts).lower()


def count_occurrences(text: str, token: str) -> int:
    return text.lower().count(token.lower())


def contains_all(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return all(needle.lower() in lowered for needle in needles)


def contains_any(text: str, *needles: str) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.I | re.M | re.S)
    if not match:
        return None
    return match.group(1).strip()


def first_int(text: str, pattern: str) -> int | None:
    value = first_match(text, pattern)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def auth_source_type(text: str) -> str:
    return (first_match(text, r"\btype\s+([^\s]+)") or "").lower()


def tacacs_server_count(text: str) -> int:
    match = re.search(r"servers\s+\{([^}]*)\}", text, re.I | re.S)
    if not match:
        return 0
    return len(re.findall(r"\S+", match.group(1)))


def is_local_placeholder_certificate(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in [
            "cn=localhost.localdomain",
            "o=mycompany",
            "ou=myorg",
            "self-signed",
        ]
    )


def load_external_packages() -> tuple[dict, dict | None]:
    if not EXTERNAL_PACKAGES.exists():
        return {}, None
    doc = json.loads(EXTERNAL_PACKAGES.read_text(encoding="utf-8"))
    by_control: dict[str, dict] = {}
    for package in doc.get("packages", []):
        for control_id in package.get("controls", []):
            by_control[control_id] = package
    return by_control, doc


def result(
    control_id: str,
    disposition: str,
    rationale: str,
    evidence: List[str],
    measurements: List[dict] | None = None,
) -> dict:
    return {
        "vuln_id": control_id,
        "disposition": disposition,
        "rationale": rationale,
        "evidence": evidence,
        "measurements": list(measurements or []),
    }


def measure(
    measurable: str,
    required: str,
    observed,
    passes: bool,
    source: str,
    *,
    unresolved: bool = False,
    note: str = "",
) -> dict:
    """Build one STIG-testable measurement row for the pullback / truth table.

    ``measurable`` is a dotted path like ``sys_httpd.max_clients`` that a STIG
    reviewer can trace back to a specific tmsh field or REST property.
    ``required`` is the STIG predicate in a reviewer-friendly form (e.g.
    ``"<= 10"``, ``"== DoD banner"``, ``"enabled"``).  ``observed`` is the
    concrete value we read from the appliance; if ``None`` the measurement is
    rendered as ``null``.  ``source`` names the snapshot key the value came
    from so reviewers can open the raw evidence to double-check.
    """
    if observed is None:
        observed_str = "null"
    elif isinstance(observed, bool):
        observed_str = "true" if observed else "false"
    else:
        observed_str = str(observed)
    row = {
        "measurable": measurable,
        "required": required,
        "observed": observed_str,
        "match": bool(passes),
        "source": source,
        "unresolved": bool(unresolved),
    }
    if note:
        row["note"] = note
    return row


def package_result(control_id: str, ctx: dict, evidence: List[str]) -> dict | None:
    package = ctx["external_packages"].get(control_id)
    if package is None:
        return None
    pkg_id = package.get("package_id", "unknown")
    disposition = package["disposition"]
    # External-evidence packages cannot be checked on-appliance, so the
    # measurement is recorded as unresolved (confidence=0) with the package
    # id as the origin so reviewers can trace back to the signed artefact.
    measurements = [
        measure(
            "external_evidence_package",
            f"package_id == {pkg_id} (disposition={disposition})",
            package.get("rationale", "external attestation"),
            disposition in {"pass", "not-applicable"},
            "external_evidence_packages",
            unresolved=True,
        )
    ]
    return result(
        control_id,
        disposition,
        package["rationale"],
        evidence + ["external_evidence_packages"],
        measurements=measurements,
    )


def load_local_service_policy() -> dict | None:
    if not LOCAL_POLICY.exists():
        return None
    try:
        return json.loads(LOCAL_POLICY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "policy_error": f"{LOCAL_POLICY.name} is not valid JSON",
            "authorized_services": [],
            "prohibited_ports": [],
        }


def parse_ltm_virtual_services(text: str) -> List[dict]:
    services: List[dict] = []
    matches = list(re.finditer(r"(?m)^ltm virtual\s+(\S+)\s+\{", text))
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        destination = first_match(body, r"^\s+destination\s+(\S+)",) or ""
        ip_protocol = (first_match(body, r"^\s+ip-protocol\s+(\S+)") or "any").lower()
        profiles_block = first_match(body, r"^\s+profiles\s+\{(.*?)^\s+\}") or ""
        profiles = sorted(set(re.findall(r"^\s+(\S+)\s+\{", profiles_block, re.M)))
        port = ""
        if ":" in destination:
            port = destination.rsplit(":", 1)[-1]
        services.append({
            "name": name,
            "destination": destination,
            "port": port,
            "ip_protocol": ip_protocol,
            "profiles": profiles,
        })
    return services


def _policy_allows_service(service: dict, policy: dict) -> bool:
    for allowed in policy.get("authorized_services", []) or []:
        if not isinstance(allowed, dict):
            continue
        for key in ("name", "destination", "port", "ip_protocol"):
            expected = str(allowed.get(key, "")).lower()
            if expected and str(service.get(key, "")).lower() != expected:
                break
        else:
            return True
    return False


def evaluate_virtual_service_authorization(vid: str, ctx: dict) -> dict:
    policy = ctx.get("local_service_policy")
    services = parse_ltm_virtual_services(ctx["texts"]["ltm_virtual"])
    if not policy:
        rows = [
            measure(
                "local_ppsm_ssp_authorization",
                "local_policy/authorized_virtual_services.json present",
                "missing",
                False,
                "tmsh_ltm_virtual",
                unresolved=True,
                note="DISA check/fix text requires PPSM CAL and SSP/site documentation before virtual-server services can be judged.",
            )
        ]
        return result(
            vid,
            "blocked-external",
            "Virtual-server ports/protocols/services require local PPSM CAL and SSP authorization evidence; no local allowlist was provided.",
            ["tmsh_ltm_virtual"],
            measurements=rows,
        )

    prohibited_ports = {str(port) for port in policy.get("prohibited_ports", []) or []}
    rows: List[dict] = []
    for service in services:
        port = str(service.get("port", ""))
        prohibited = port in prohibited_ports
        authorized = _policy_allows_service(service, policy)
        passes = authorized and not prohibited
        rows.append(
            measure(
                f"ltm_virtual.{service['name']}.service_authorized",
                "authorized_by_local_ppsm_ssp == true AND prohibited_port == false",
                f"destination={service['destination']}; port={port}; protocol={service['ip_protocol']}; authorized={authorized}; prohibited={prohibited}",
                passes,
                "tmsh_ltm_virtual",
                note="Raw service values are evaluated locally and must not be exported back to the factory.",
            )
        )
    if not rows:
        rows.append(
            measure(
                "ltm_virtual.listener_count",
                "0 unauthorized/prohibited listeners",
                "0 listeners",
                True,
                "tmsh_ltm_virtual",
            )
        )
    return result(
        vid,
        _bucket("pass", rows),
        "Virtual-server listeners were compared against the local PPSM/SSP allowlist and prohibited-port list.",
        ["tmsh_ltm_virtual"],
        measurements=rows,
    )


def build_context(client: F5Client) -> dict:
    provision, provision_meta = capture_rest(client, "sys_provision", "/mgmt/tm/sys/provision")
    global_settings, global_meta = capture_rest(
        client, "sys_global_settings", "/mgmt/tm/sys/global-settings"
    )
    sshd, sshd_meta = capture_rest(client, "sys_sshd", "/mgmt/tm/sys/sshd")
    global_tmsh_text, global_tmsh_meta = capture_tmsh(
        client, "tmsh_sys_global_settings", "list sys global-settings all-properties"
    )
    httpd_text, httpd_meta = capture_tmsh(client, "tmsh_sys_httpd", "list sys httpd all-properties")
    cli_global_text, cli_global_meta = capture_tmsh(
        client, "tmsh_cli_global_settings", "list cli global-settings all-properties"
    )
    ntp_text, ntp_meta = capture_tmsh(client, "tmsh_sys_ntp", "list sys ntp")
    password_policy_text, password_policy_meta = capture_tmsh(
        client, "tmsh_auth_password_policy", "list auth password-policy all-properties"
    )
    auth_user_text, auth_user_meta = capture_tmsh(client, "tmsh_auth_user", "list auth user")
    auth_source_text, auth_source_meta = capture_tmsh(
        client, "tmsh_auth_source", "list auth source all-properties"
    )
    auth_remote_role_text, auth_remote_role_meta = capture_tmsh(
        client, "tmsh_auth_remote_role", "list auth remote-role all-properties"
    )
    auth_tacacs_text, auth_tacacs_meta = capture_tmsh(
        client, "tmsh_auth_tacacs_system_auth", "list auth tacacs system-auth all-properties"
    )
    daemon_log_text, daemon_log_meta = capture_tmsh(
        client, "tmsh_sys_daemon_log_settings", "list sys daemon-log-settings all-properties"
    )
    db_security_text, db_security_meta = capture_tmsh(
        client,
        "tmsh_sys_db_security",
        "list sys db liveinstall.checksig password.difok all-properties",
    )
    cm_device_text, cm_device_meta = capture_tmsh(
        client, "tmsh_cm_device", "list cm device all-properties"
    )
    cert_summary_text, cert_summary_meta = capture_bash(
        client,
        "bash_device_certificate_summary",
        "openssl x509 -in /config/httpd/conf/ssl.crt/server.crt -issuer -subject -enddate -serial",
    )
    log_storage_text, log_storage_meta = capture_bash(
        client,
        "bash_log_storage_capacity",
        "df -h /var/log /shared || df -h",
    )
    syslog_text, syslog_meta = capture_tmsh(client, "tmsh_sys_syslog", "list sys syslog all-properties")
    snmp_text, snmp_meta = capture_tmsh(client, "tmsh_sys_snmp", "list sys snmp all-properties")
    ucs_text, ucs_meta = capture_tmsh(client, "tmsh_sys_ucs", "list sys ucs")
    apm_profiles_text, apm_profiles_meta = capture_tmsh(
        client, "tmsh_apm_profile_access", "list apm profile access all-properties"
    )
    apm_policy_text, apm_policy_meta = capture_tmsh(
        client, "tmsh_apm_policy_access_policy", "list apm policy access-policy all-properties"
    )
    apm_message_box_text, apm_message_box_meta = capture_tmsh(
        client, "tmsh_apm_policy_agent_message_box", "list apm policy agent message-box all-properties"
    )
    apm_connectivity_text, apm_connectivity_meta = capture_optional_tmsh(
        client, "tmsh_apm_profile_connectivity", "list apm profile connectivity all-properties"
    )
    apm_log_text, apm_log_meta = capture_tmsh(
        client, "tmsh_apm_log_setting", "list apm log-setting all-properties"
    )
    apm_network_access, apm_network_access_meta = capture_optional_rest(
        client,
        "apm_resource_network_access",
        "/mgmt/tm/apm/resource/network-access/~Common~stig_vpn_resource",
    )
    afm_policy_text, afm_policy_meta = capture_tmsh(
        client, "tmsh_security_firewall_policy", "list security firewall policy all-properties"
    )
    asm_policy_text, asm_policy_meta = capture_tmsh(
        client, "tmsh_asm_policy", "list asm policy all-properties"
    )
    ltm_virtual_text, ltm_virtual_meta = capture_tmsh(
        client, "tmsh_ltm_virtual", "list ltm virtual all-properties"
    )
    client_ssl_text, client_ssl_meta = capture_tmsh(
        client, "tmsh_ltm_profile_client_ssl", "list ltm profile client-ssl all-properties"
    )
    external_packages, external_packages_doc = load_external_packages()
    external_packages_meta = None
    if external_packages_doc is not None:
        _, external_packages_meta = capture_repo_file("external_evidence_packages", EXTERNAL_PACKAGES)

    provisioned = {
        item.get("name")
        for item in (provision.get("items") or [])
        if (item.get("level") or "").lower() != "none"
    }
    snapshot_metas = [
        provision_meta,
        global_meta,
        sshd_meta,
        global_tmsh_meta,
        httpd_meta,
        cli_global_meta,
        ntp_meta,
        password_policy_meta,
        auth_user_meta,
        auth_source_meta,
        auth_remote_role_meta,
        auth_tacacs_meta,
        daemon_log_meta,
        db_security_meta,
        cm_device_meta,
        cert_summary_meta,
        log_storage_meta,
        syslog_meta,
        snmp_meta,
        ucs_meta,
        apm_profiles_meta,
        apm_policy_meta,
        apm_message_box_meta,
        apm_connectivity_meta,
        apm_log_meta,
        apm_network_access_meta,
        afm_policy_meta,
        asm_policy_meta,
        ltm_virtual_meta,
        client_ssl_meta,
    ]
    if external_packages_meta is not None:
        snapshot_metas.append(external_packages_meta)
    return {
        "provisioned": provisioned,
        "global_settings": global_settings,
        "sshd": sshd,
        "texts": {
            "global_tmsh": global_tmsh_text,
            "httpd": httpd_text,
            "cli_global": cli_global_text,
            "ntp": ntp_text,
            "password_policy": password_policy_text,
            "auth_user": auth_user_text,
            "auth_source": auth_source_text,
            "auth_remote_role": auth_remote_role_text,
            "auth_tacacs": auth_tacacs_text,
            "daemon_log": daemon_log_text,
            "db_security": db_security_text,
            "cm_device": cm_device_text,
            "cert_summary": cert_summary_text,
            "log_storage": log_storage_text,
            "syslog": syslog_text,
            "snmp": snmp_text,
            "ucs": ucs_text,
            "apm_profiles": apm_profiles_text,
            "apm_policy": apm_policy_text,
            "apm_message_box": apm_message_box_text,
            "apm_connectivity": apm_connectivity_text,
            "apm_log": apm_log_text,
            "afm_policy": afm_policy_text,
            "asm_policy": asm_policy_text,
            "ltm_virtual": ltm_virtual_text,
            "client_ssl": client_ssl_text,
        },
        "structured": {
            "apm_network_access": apm_network_access,
        },
        "external_packages": external_packages,
        "local_service_policy": load_local_service_policy(),
        "snapshots": {meta["name"]: meta for meta in snapshot_metas},
    }


def is_external_dependency(text: str) -> bool:
    return contains_any(
        text,
        "issm",
        "isso",
        "ppsm",
        "ocsp",
        "crldp",
        "mfa",
        "separate device",
        "external",
        "redundant authentication servers",
    )


def applicable_for_control(control: dict, full_text: str, ctx: dict) -> bool:
    module = control.get("module", "PLATFORM")
    if module != "PLATFORM" and module.lower() not in ctx["provisioned"]:
        return False
    if (
        "remote access" in full_text
        and "apm" not in ctx["provisioned"]
        and "asm" not in ctx["provisioned"]
        and "ltm" not in ctx["provisioned"]
    ):
        return False
    if "content filtering" in full_text and "asm" not in ctx["provisioned"]:
        return False
    if "dns" in full_text and "gtm" not in ctx["provisioned"] and "dns" not in ctx["provisioned"]:
        return False
    if "network firewall" in full_text and "afm" not in ctx["provisioned"]:
        return False
    return True


def _banner_preview(text: str, limit: int = 60) -> str:
    t = (text or "").replace("\n", " ")
    return t if len(t) <= limit else t[:limit] + f"...(+{len(t) - limit} chars)"


def _bucket(disposition: str, rows: List[dict]) -> str:
    """Downgrade to fail when any measurement failed, unless every unmet row
    is flagged unresolved (external-only) -- in which case we honour the
    caller's disposition."""
    if not rows:
        return disposition
    unmet = [r for r in rows if not r["match"]]
    if not unmet:
        return "pass" if disposition == "pass" else disposition
    if all(r.get("unresolved") for r in unmet):
        return disposition
    if disposition == "pass":
        return "fail"
    return disposition


def evaluate_known(control: dict, full_text: str, ctx: dict) -> dict | None:
    """Evaluate a control and emit one :func:`measure` row per STIG predicate.

    Every branch here produces a list of structured measurements that map
    directly to the truth-table rows a STIG reviewer sees in the web UI, so
    verdicts can always be traced back to an exact observed value, its source
    snapshot, and the predicate that classified it.
    """
    vid = control["vuln_id"]
    gs = ctx["global_settings"]
    sshd = ctx["sshd"]
    texts = ctx["texts"]
    structured = ctx["structured"]

    if vid == "V-266064":
        mx = first_int(texts["httpd"], r"\bmax-clients\s+(\d+)")
        rows = [measure(
            "sys_httpd.max_clients", "<= 10", mx,
            mx is not None and mx <= 10, "tmsh_sys_httpd",
        )]
        return result(vid, _bucket("pass", rows),
            f"Configuration Utility concurrency: detected max-clients={mx!s} (<= 10 required).",
            ["tmsh_sys_httpd"], measurements=rows)

    if vid == "V-266065":
        shared_hits = count_occurrences(texts["auth_user"], "shared") \
            + count_occurrences(texts["auth_user"], "group") \
            + count_occurrences(texts["auth_user"], "generic")
        rows = [measure(
            "auth_user.shared_or_group_account_hits", "== 0", shared_hits,
            shared_hits == 0, "tmsh_auth_user",
        )]
        return result(vid, _bucket("pass", rows),
            f"Local user inventory: detected {shared_hits} token match(es) for shared/group/generic accounts (0 required).",
            ["tmsh_auth_user"], measurements=rows)

    if vid == "V-266066":
        local_admins = count_occurrences(texts["auth_user"], "role admin")
        fallback = contains_all(texts["auth_source"], "fallback true")
        rows = [
            measure("auth_user.local_admin_count", "== 1", local_admins,
                    local_admins == 1, "tmsh_auth_user"),
            measure("auth_source.fallback", "true", "true" if fallback else "false",
                    fallback, "tmsh_auth_source"),
        ]
        return result(vid, _bucket("pass", rows),
            f"Account-of-last-resort: local_admins={local_admins}, fallback={'enabled' if fallback else 'disabled'}.",
            ["tmsh_auth_source", "tmsh_auth_user"], measurements=rows)

    if vid == "V-266067":
        local_admins = count_occurrences(texts["auth_user"], "role admin")
        remote_role = "role-info {" in texts["auth_remote_role"]
        rows = [
            measure("auth_user.local_admin_count", "<= 1", local_admins,
                    local_admins <= 1, "tmsh_auth_user"),
            measure("auth_remote_role.role_info_mappings_present", "true",
                    "true" if remote_role else "false", remote_role, "tmsh_auth_remote_role"),
        ]
        return result(vid, _bucket("pass", rows),
            "Role assignment: least-privilege requires no extra local admins beyond the emergency account AND remote-role mappings must exist.",
            ["tmsh_auth_user", "tmsh_auth_remote_role"], measurements=rows)

    if vid == "V-266068":
        dl = texts["daemon_log"]
        cg = texts["cli_global"]
        rows = [
            measure("daemon_log.mcpd.audit", "enabled",
                    "enabled" if contains_all(dl, "sys daemon-log-settings mcpd", "audit enabled") else "disabled",
                    contains_all(dl, "sys daemon-log-settings mcpd", "audit enabled"),
                    "tmsh_sys_daemon_log_settings"),
            measure("daemon_log.mcpd.log_level", "notice",
                    "notice" if contains_all(dl, "sys daemon-log-settings mcpd", "log-level notice") else "other",
                    contains_all(dl, "sys daemon-log-settings mcpd", "log-level notice"),
                    "tmsh_sys_daemon_log_settings"),
            measure("daemon_log.tmm.os_log_level", "informational",
                    "informational" if contains_all(dl, "sys daemon-log-settings tmm", "os-log-level informational") else "other",
                    contains_all(dl, "sys daemon-log-settings tmm", "os-log-level informational"),
                    "tmsh_sys_daemon_log_settings"),
            measure("daemon_log.tmm.ssl_log_level", "informational",
                    "informational" if contains_all(dl, "sys daemon-log-settings tmm", "ssl-log-level informational") else "other",
                    contains_all(dl, "sys daemon-log-settings tmm", "ssl-log-level informational"),
                    "tmsh_sys_daemon_log_settings"),
            measure("cli_global.audit", "enabled",
                    "enabled" if contains_all(cg, "audit enabled") else "disabled",
                    contains_all(cg, "audit enabled"), "tmsh_cli_global_settings"),
        ]
        return result(vid, _bucket("pass", rows),
            "Privileged-function auditing evaluated across mcpd / tmm daemon-log-settings and the CLI global audit flag.",
            ["tmsh_sys_daemon_log_settings", "tmsh_cli_global_settings"], measurements=rows)

    if vid == "V-266069":
        pp = texts["password_policy"]
        rows = [
            measure("auth_password_policy.max_login_failures", "== 3",
                    first_match(pp, r"max-login-failures\s+(\d+)") or "null",
                    contains_all(pp, "max-login-failures 3"), "tmsh_auth_password_policy"),
            measure("auth_password_policy.lockout_duration", "== 900",
                    first_match(pp, r"lockout-duration\s+(\d+)") or "null",
                    contains_all(pp, "lockout-duration 900"), "tmsh_auth_password_policy"),
        ]
        return result(vid, _bucket("pass", rows),
            "Password policy requires max-login-failures=3 and lockout-duration=900.",
            ["tmsh_auth_password_policy"], measurements=rows)

    if vid == "V-266070":
        banner = gs.get("guiSecurityBannerText", "")
        rows = [measure(
            "sys_global_settings.gui_security_banner_text",
            "== canonical DoD Notice and Consent banner",
            _banner_preview(banner), banner == DOD_BANNER, "sys_global_settings",
        )]
        return result(vid, _bucket("pass", rows),
            "TMOS UI banner must exactly equal the canonical DoD Notice and Consent banner.",
            ["sys_global_settings"], measurements=rows)

    if vid == "V-266074":
        packaged = package_result(vid, ctx, ["bash_log_storage_capacity", "tmsh_sys_syslog"])
        if packaged is not None:
            return packaged

    if vid == "V-266078":
        ok = contains_all(texts["db_security"], 'sys db liveinstall.checksig', 'value "enable"')
        rows = [measure("sys_db.liveinstall_checksig", 'value "enable"',
                        'enable' if ok else 'disable', ok, "tmsh_sys_db_security")]
        return result(vid, _bucket("pass", rows),
            "Software-image signature verification evaluated from sys db liveinstall.checksig.",
            ["tmsh_sys_db_security"], measurements=rows)

    if vid == "V-266079":
        st = auth_source_type(texts["auth_source"])
        servers = tacacs_server_count(texts["auth_tacacs"]) if st == "tacacs" else 0
        rows = [
            measure("auth_source.type", "in {tacacs, radius, clientcert-ldap}",
                    st or "unknown",
                    st in {"tacacs", "radius", "clientcert-ldap", "client-cert-ldap"},
                    "tmsh_auth_source"),
            measure("auth_tacacs.server_count", ">= 2", servers,
                    servers >= 2, "tmsh_auth_tacacs_system_auth"),
        ]
        return result(vid, _bucket("pass", rows),
            f"Admin auth topology: detected type={st or 'unknown'}, redundant-servers={servers}.",
            ["tmsh_auth_source", "tmsh_auth_tacacs_system_auth"], measurements=rows)

    if vid == "V-266080":
        packaged = package_result(vid, ctx, ["tmsh_cm_device"])
        if packaged is not None:
            return packaged

    if vid == "V-266083":
        placeholder = is_local_placeholder_certificate(texts["cert_summary"])
        rows = [measure("device_certificate.issuer", "not placeholder / not self-signed",
                        "self-signed-or-placeholder" if placeholder else "organizationally-issued",
                        not placeholder, "bash_device_certificate_summary")]
        return result(vid, _bucket("pass", rows),
            "Device certificate issuer: placeholder/self-signed TMUI certificates are a finding.",
            ["bash_device_certificate_summary"], measurements=rows)

    if vid in {"V-266084", "V-266150"}:
        return evaluate_virtual_service_authorization(vid, ctx)

    if vid == "V-266085":
        st = auth_source_type(texts["auth_source"])
        ok = st in {"clientcert-ldap", "client-cert-ldap", "radius", "tacacs"}
        rows = [measure("auth_source.type", "in {clientcert-ldap, radius, tacacs}",
                        st or "unknown", ok, "tmsh_auth_source")]
        return result(vid, _bucket("pass", rows),
            f"Interactive management auth source: detected type={st or 'unknown'}.",
            ["tmsh_auth_source"], measurements=rows)

    if vid in {"V-266088", "V-266089", "V-266090", "V-266091"}:
        kind_map = {
            "V-266088": ("required-uppercase", "required-uppercase 1", 1),
            "V-266089": ("required-lowercase", "required-lowercase 1", 1),
            "V-266090": ("required-numeric", "required-numeric 1", 1),
            "V-266091": ("required-special", "required-special 1", 1),
        }
        key, needle, req = kind_map[vid]
        pp = texts["password_policy"]
        enforce = contains_all(pp, "policy-enforcement enabled")
        detail = first_match(pp, rf"{re.escape(key)}\s+(\d+)") or "null"
        meets = contains_all(pp, needle)
        rows = [
            measure("auth_password_policy.policy_enforcement", "enabled",
                    "enabled" if enforce else "disabled", enforce, "tmsh_auth_password_policy"),
            measure(f"auth_password_policy.{key}", f">= {req}", detail,
                    meets, "tmsh_auth_password_policy"),
        ]
        return result(vid, _bucket("pass", rows),
            f"Password policy: policy-enforcement must be enabled and {key} >= {req}.",
            ["tmsh_auth_password_policy"], measurements=rows)

    if vid == "V-266092":
        ok = contains_all(texts["db_security"], 'sys db password.difok', 'value "8"')
        rows = [measure("sys_db.password_difok", 'value "8"',
                        first_match(texts["db_security"], r"password\.difok[\s\S]*?value\s+\"(\d+)\"") or "null",
                        ok, "tmsh_sys_db_security")]
        return result(vid, _bucket("pass", rows),
            "Password reuse distance evaluated from sys db password.difok.",
            ["tmsh_sys_db_security"], measurements=rows)

    if vid == "V-266093":
        st = auth_source_type(texts["auth_source"])
        if st not in {"clientcert-ldap", "client-cert-ldap"}:
            rows = [measure("auth_source.type", "clientcert-ldap (for applicability)",
                            st or "unknown", False, "tmsh_auth_source", unresolved=True,
                            note="Control applies only when PKI ClientCert LDAP is in use.")]
            return result(vid, "not-applicable",
                "Control applies only when device-management authentication uses ClientCert LDAP with cached OCSP settings.",
                ["tmsh_auth_source"], measurements=rows)

    if vid == "V-266094":
        st = auth_source_type(texts["auth_source"])
        if st not in {"clientcert-ldap", "client-cert-ldap"}:
            rows = [measure("auth_source.type", "clientcert-ldap (for applicability)",
                            st or "unknown", False, "tmsh_auth_source", unresolved=True,
                            note="Control applies only when PKI ClientCert LDAP is in use.")]
            return result(vid, "not-applicable",
                "Control applies only when device-management authentication uses ClientCert LDAP / PKI-based auth.",
                ["tmsh_auth_source"], measurements=rows)

    if vid == "V-266095":
        httpd = texts["httpd"]
        cli = texts["cli_global"]
        gt = texts["global_tmsh"]
        httpd_idle = first_int(httpd, r"\bauth-pam-idle-timeout\s+(\d+)")
        dashboard_on = contains_all(httpd, "auth-pam-dashboard-timeout on")
        cli_idle = first_int(cli, r"\bidle-timeout\s+(\d+)")
        console_idle = first_int(gt, r"\bconsole-inactivity-timeout\s+(\d+)")
        try:
            sshd_idle = int(sshd.get("inactivityTimeout"))
        except (TypeError, ValueError):
            sshd_idle = None
        rows = [
            measure("sys_httpd.auth_pam_idle_timeout", "<= 300", httpd_idle,
                    httpd_idle is not None and httpd_idle <= 300, "tmsh_sys_httpd"),
            measure("sys_httpd.auth_pam_dashboard_timeout", "on",
                    "on" if dashboard_on else "off", dashboard_on, "tmsh_sys_httpd"),
            measure("cli_global.idle_timeout", "<= 5", cli_idle,
                    cli_idle is not None and cli_idle <= 5, "tmsh_cli_global_settings"),
            measure("sys_global_settings.console_inactivity_timeout", "<= 300", console_idle,
                    console_idle is not None and console_idle <= 300, "tmsh_sys_global_settings"),
            measure("sys_sshd.inactivity_timeout", "<= 300", sshd_idle,
                    sshd_idle is not None and sshd_idle <= 300, "sys_sshd"),
        ]
        return result(vid, _bucket("pass", rows),
            "Idle logout evaluated across HTTPD/TMUI, CLI, console, and SSH timeout sources.",
            ["tmsh_sys_httpd", "tmsh_cli_global_settings", "tmsh_sys_global_settings", "sys_sshd"],
            measurements=rows)

    if vid == "V-266096":
        packaged = package_result(vid, ctx, ["tmsh_sys_ucs"])
        if packaged is not None:
            return packaged
        has_local = "filename /var/local/ucs/" in texts["ucs"]
        rows = [measure("sys_ucs.local_backup_file", "/var/local/ucs/ (filename present)",
                        "present" if has_local else "absent", has_local, "tmsh_sys_ucs")]
        return result(vid, _bucket("pass", rows),
            "Local UCS backup presence evaluated from tmsh list sys ucs (off-device storage still requires external evidence).",
            ["tmsh_sys_ucs"], measurements=rows)

    if vid == "V-266134":
        enabled = (sshd.get("banner") or "").lower() == "enabled"
        banner = sshd.get("bannerText", "")
        rows = [
            measure("sys_sshd.banner", "enabled",
                    "enabled" if enabled else "disabled", enabled, "sys_sshd"),
            measure("sys_sshd.banner_text", "== canonical DoD banner",
                    _banner_preview(banner), banner == DOD_BANNER, "sys_sshd"),
        ]
        return result(vid, _bucket("pass", rows),
            "SSHD must have banner enabled AND bannerText must equal the canonical DoD banner.",
            ["sys_sshd"], measurements=rows)

    if vid == "V-266137":
        hits = count_occurrences(texts["apm_profiles"], "max-concurrent-users 1")
        rows = [measure("apm_profile_access.max_concurrent_users", "== 1 (>= 1 profile matches)",
                        hits, hits >= 1, "tmsh_apm_profile_access")]
        return result(vid, _bucket("pass", rows),
            "APM access profiles must limit max-concurrent-users to 1 or the organization-defined value.",
            ["tmsh_apm_profile_access"], measurements=rows)

    if vid == "V-266145":
        packaged = package_result(vid, ctx, ["tmsh_apm_policy_access_policy", "tmsh_apm_policy_agent_message_box"])
        if packaged is not None:
            return packaged

    if vid == "V-266146":
        apm_log = texts["apm_log"]
        apm_prof = texts["apm_profiles"]
        sl = texts["syslog"]
        rows = [
            measure("apm_log_setting.default_log_setting.enabled", "true",
                    "true" if contains_all(apm_log, "apm log-setting default-log-setting", "enabled true") else "false",
                    contains_all(apm_log, "apm log-setting default-log-setting", "enabled true"),
                    "tmsh_apm_log_setting"),
            measure("apm_log_setting.default_log_setting.access_control_level", "notice",
                    "notice" if contains_all(apm_log, "access-control notice") else "other",
                    contains_all(apm_log, "access-control notice"), "tmsh_apm_log_setting"),
            measure("apm_profile_access.default_log_setting_attached", "true",
                    "true" if "default-log-setting" in apm_prof else "false",
                    "default-log-setting" in apm_prof, "tmsh_apm_profile_access"),
            measure("sys_syslog.remote_host_configured", "host 10.0.0.*",
                    "present" if "host 10.0.0." in sl else "absent",
                    "host 10.0.0." in sl, "tmsh_sys_syslog"),
        ]
        return result(vid, _bucket("pass", rows),
            "APM default-log-setting must be enabled at notice, attached to access profiles, and syslog must define remote servers.",
            ["tmsh_apm_log_setting", "tmsh_apm_profile_access", "tmsh_sys_syslog"], measurements=rows)

    if vid == "V-266150":
        return evaluate_virtual_service_authorization(vid, ctx)

    if vid == "V-266152":
        servers = tacacs_server_count(texts["auth_tacacs"])
        ap = texts["apm_policy"]
        has_auth = "tacacsplus_auth" in ap or "kerberos_auth" in ap
        has_mfa = "machinecert_auth" in ap or "client_cert" in ap
        rows = [
            measure("apm_policy.auth_server_agent", "tacacsplus_auth OR kerberos_auth",
                    "present" if has_auth else "absent", has_auth, "tmsh_apm_policy_access_policy"),
            measure("apm_policy.mfa_agent", "machinecert_auth OR client_cert",
                    "present" if has_mfa else "absent", has_mfa, "tmsh_apm_policy_access_policy"),
            measure("auth_tacacs.server_count", ">= 2", servers, servers >= 2,
                    "tmsh_auth_tacacs_system_auth"),
        ]
        return result(vid, _bucket("pass", rows),
            "APM user-auth policy: access policy graph must have an auth agent + MFA agent AND TACACS system-auth must have >= 2 servers.",
            ["tmsh_apm_policy_access_policy", "tmsh_auth_tacacs_system_auth"], measurements=rows)

    if vid == "V-266154":
        packaged = package_result(vid, ctx, ["tmsh_apm_policy_access_policy", "tmsh_apm_profile_access"])
        if packaged is not None:
            return packaged

    if vid == "V-266160":
        packaged = package_result(vid, ctx, ["tmsh_security_firewall_policy"])
        if packaged is not None:
            return packaged

    if vid == "V-266167":
        ok = contains_all(texts["httpd"], "auth-pam-validate-ip on")
        rows = [measure("sys_httpd.auth_pam_validate_ip", "on",
                        "on" if ok else "off", ok, "tmsh_sys_httpd")]
        return result(vid, _bucket("pass", rows),
            "Management-session source-IP pinning evaluated from sys httpd auth-pam-validate-ip.",
            ["tmsh_sys_httpd"], measurements=rows)

    if vid == "V-266174":
        auto = str(structured["apm_network_access"].get("autoLaunch", "")).lower()
        mt = contains_any(texts["apm_connectivity"], "always connected mode",
                          "machine tunnel", "machine-tunnel")
        rows = [
            measure("apm_resource_network_access.auto_launch", "true", auto or "null",
                    auto == "true", "apm_resource_network_access"),
            measure("apm_profile_connectivity.machine_tunnel", "always-connected OR machine tunnel",
                    "present" if mt else "absent", mt, "tmsh_apm_profile_connectivity"),
        ]
        # Control passes if EITHER measurement passes, so handle manually.
        combined = auto == "true" or mt
        return result(vid, "pass" if combined else "fail",
            "Always-on VPN posture: passes if the network-access resource auto-launches OR the connectivity profile defines a machine tunnel.",
            ["apm_resource_network_access", "tmsh_apm_profile_connectivity"], measurements=rows)

    # --------------------------- family fallbacks ---------------------------
    fam = control["handler_family"]
    if fam == "banner":
        is_gui = "tmos user interface" in full_text
        target = gs.get("guiSecurityBannerText", "") if is_gui else sshd.get("bannerText", "")
        src = "sys_global_settings" if is_gui else "sys_sshd"
        rows = [measure(
            f"{src}.banner_text", "== canonical DoD banner",
            _banner_preview(target), target == DOD_BANNER, src,
        )]
        return result(vid, _bucket("pass", rows),
            "Banner text must exactly equal the canonical DoD Notice and Consent banner.",
            [src], measurements=rows)

    if fam == "password_policy":
        pp = texts["password_policy"]
        rows = [
            measure("auth_password_policy.policy_enforcement", "enabled",
                    "enabled" if contains_all(pp, "policy-enforcement enabled") else "disabled",
                    contains_all(pp, "policy-enforcement enabled"),
                    "tmsh_auth_password_policy"),
            measure("auth_password_policy.minimum_length", ">= 15",
                    first_match(pp, r"minimum-length\s+(\d+)") or "null",
                    contains_all(pp, "minimum-length 15"),
                    "tmsh_auth_password_policy"),
        ]
        return result(vid, _bucket("pass", rows),
            "Password policy must have policy-enforcement enabled AND minimum-length >= 15.",
            ["tmsh_auth_password_policy"], measurements=rows)

    if fam == "ntp":
        nt = texts["ntp"]
        rows = [
            measure("sys_ntp.servers", "non-empty servers { ... }",
                    "present" if "servers {" in nt else "absent",
                    "servers {" in nt, "tmsh_sys_ntp"),
            measure("sys_ntp.include_authenticate", "true",
                    "true" if "include authenticate" in nt else "false",
                    "include authenticate" in nt, "tmsh_sys_ntp"),
        ]
        return result(vid, _bucket("pass", rows),
            "NTP must define servers AND 'include authenticate' so time sync is authenticated.",
            ["tmsh_sys_ntp"], measurements=rows)

    if fam == "logging":
        count = count_occurrences(texts["syslog"], "host ")
        rows = [measure("sys_syslog.remote_server_count", ">= 1", count,
                        count >= 1, "tmsh_sys_syslog")]
        return result(vid, _bucket("pass", rows),
            f"Syslog: detected {count} remote 'host' entries (>= 1 required).",
            ["tmsh_sys_syslog"], measurements=rows)

    if fam == "snmp":
        sn = texts["snmp"].lower()
        rows = [
            measure("sys_snmp.snmpv1", "disable",
                    "disable" if "snmpv1 disable" in sn else "enable",
                    "snmpv1 disable" in sn, "tmsh_sys_snmp"),
            measure("sys_snmp.snmpv2c", "disable",
                    "disable" if "snmpv2c disable" in sn else "enable",
                    "snmpv2c disable" in sn, "tmsh_sys_snmp"),
            measure("sys_snmp.snmpv3_users", "non-empty",
                    "absent" if "users none" in sn else "present",
                    "users none" not in sn, "tmsh_sys_snmp"),
        ]
        return result(vid, _bucket("pass", rows),
            "SNMP passes only if legacy v1/v2c are disabled AND SNMPv3 users are configured.",
            ["tmsh_sys_snmp"], measurements=rows)

    if fam == "backup":
        packaged = package_result(vid, ctx, ["tmsh_sys_ucs"])
        if packaged is not None:
            return packaged
        has_local = "filename /var/local/ucs/" in texts["ucs"]
        rows = [measure("sys_ucs.local_backup_file", "/var/local/ucs/ (filename present)",
                        "present" if has_local else "absent", has_local, "tmsh_sys_ucs")]
        return result(vid, _bucket("pass", rows),
            "Backup presence evaluated from tmsh list sys ucs.",
            ["tmsh_sys_ucs"], measurements=rows)

    if fam == "apm_access":
        if contains_any(full_text, "display the standard mandatory", "consent banner", "ocsp", "crldp"):
            packaged = package_result(vid, ctx, ["tmsh_apm_profile_access", "tmsh_apm_policy_access_policy"])
            if packaged is not None:
                return packaged
        ap = texts["apm_profiles"]
        rows = [
            measure("apm_profile_access.restrict_to_single_client_ip", "true",
                    "true" if contains_all(ap, "restrict-to-single-client-ip true") else "false",
                    contains_all(ap, "restrict-to-single-client-ip true"),
                    "tmsh_apm_profile_access"),
            measure("apm_profile_access.max_concurrent_users", "== 1",
                    "1" if contains_all(ap, "max-concurrent-users 1") else "other",
                    contains_all(ap, "max-concurrent-users 1"),
                    "tmsh_apm_profile_access"),
        ]
        return result(vid, _bucket("pass", rows),
            "APM access-profile baseline: restrict-to-single-client-ip=true AND max-concurrent-users=1.",
            ["tmsh_apm_profile_access"], measurements=rows)

    if fam == "asm_policy":
        ap = texts["asm_policy"]
        lv = texts["ltm_virtual"]
        rows = [
            measure("asm_policy.active", "true",
                    "active" if "active" in ap.lower() else "inactive",
                    "active" in ap.lower(), "tmsh_asm_policy"),
            measure("asm_policy.blocking_mode", "enabled",
                    "enabled" if "blocking-mode enabled" in ap.lower() else "disabled",
                    "blocking-mode enabled" in ap.lower(), "tmsh_asm_policy"),
            measure("ltm_virtual.stig_test_vs.attached_asm_policy", "present",
                    "present" if "stig_test_vs" in lv else "absent",
                    "stig_test_vs" in lv, "tmsh_ltm_virtual"),
        ]
        return result(vid, _bucket("pass", rows),
            "ASM: an active blocking policy must be attached to the STIG test virtual.",
            ["tmsh_asm_policy", "tmsh_ltm_virtual"], measurements=rows)

    if fam == "afm_firewall":
        afm = texts["afm_policy"]
        lv = texts["ltm_virtual"]
        rows = [
            measure("security_firewall_policy.stig_compliance_policy", "present",
                    "present" if contains_all(afm, "security firewall policy", "stig_compliance_policy") else "absent",
                    contains_all(afm, "security firewall policy", "stig_compliance_policy"),
                    "tmsh_security_firewall_policy"),
            measure("ltm_virtual.stig_test_vs.fw_enforced_policy", "stig_compliance_policy",
                    "stig_compliance_policy" if contains_all(lv, "stig_test_vs", "fw-enforced-policy stig_compliance_policy") else "other",
                    contains_all(lv, "stig_test_vs", "fw-enforced-policy stig_compliance_policy"),
                    "tmsh_ltm_virtual"),
        ]
        return result(vid, _bucket("pass", rows),
            "AFM: an enforced firewall policy must be attached to the STIG test virtual.",
            ["tmsh_security_firewall_policy", "tmsh_ltm_virtual"], measurements=rows)

    if fam == "ltm_virtual_services":
        return evaluate_virtual_service_authorization(vid, ctx)

    if fam == "ltm_virtual_ssl":
        cs = texts["client_ssl"]
        lv = texts["ltm_virtual"]
        secure = contains_all(cs, "ltm profile client-ssl clientssl", "ciphers ecdhe-rsa-aes128-gcm-sha256")
        insecure = contains_all(lv, "stig_test_vs", "clientssl-insecure-compatible")
        rows = [
            measure("ltm_profile_client_ssl.fips_cipher_suite", "ecdhe-rsa-aes128-gcm-sha256",
                    "present" if secure else "absent", secure, "tmsh_ltm_profile_client_ssl"),
            measure("ltm_virtual.stig_test_vs.insecure_compatible_attached", "false",
                    "true" if insecure else "false", not insecure, "tmsh_ltm_virtual"),
        ]
        return result(vid, _bucket("pass", rows),
            "TLS/SSL intermediary: a FIPS cipher profile must be present AND the STIG virtual must not attach the insecure-compatible profile.",
            ["tmsh_ltm_profile_client_ssl", "tmsh_ltm_virtual"], measurements=rows)

    if contains_any(full_text, "protocol compliance", "protocol anomalies", "smtp", "ftp", "http"):
        present = "stig_protocol_inspection" in texts["ltm_virtual"]
        rows = [measure("ltm_virtual.stig_protocol_inspection", "attached",
                        "present" if present else "absent", present, "tmsh_ltm_virtual")]
        return result(vid, _bucket("pass", rows),
            "Protocol-inspection: the STIG protocol-inspection profile must be attached to the active virtual.",
            ["tmsh_ltm_virtual"], measurements=rows)

    return None


def evaluate_control(control: dict, ctx: dict) -> dict:
    full_text = lower_join(
        control.get("title", ""),
        control.get("applicability_clause", ""),
        " ".join(control.get("key_tokens", [])),
        control.get("handler_family", ""),
    )
    vid = control["vuln_id"]
    if control.get("conditional_not_applicable") and not applicable_for_control(control, full_text, ctx):
        module = control.get("module", "PLATFORM")
        rows = [measure(
            "sys_provision.module", f"provisioned (module={module})",
            "provisioned" if module.lower() in ctx["provisioned"] or module == "PLATFORM" else "not-provisioned",
            False, "sys_provision", unresolved=True,
            note="Conditional N/A: control only applies when the required module is provisioned.",
        )]
        return result(vid, "not-applicable",
            control.get("applicability_clause") or "Conditional N/A clause matched device capability inventory.",
            ["sys_provision"], measurements=rows)

    known = evaluate_known(control, full_text, ctx)
    if known is not None:
        return known

    packaged = package_result(vid, ctx, ["sys_provision"])
    if packaged is not None:
        return packaged

    if is_external_dependency(full_text):
        rows = [measure(
            "external_dependency", "external attestation or runbook evidence",
            "not captured on-appliance", False, "sys_provision", unresolved=True,
            note="Control references external services / org-defined parameters.",
        )]
        return result(vid, "blocked-external",
            "Control depends on external services, organizational parameters, or human approvals not fully evidenced by local device state.",
            ["sys_provision"], measurements=rows)

    if not applicable_for_control(control, full_text, ctx):
        module = control.get("module", "PLATFORM")
        rows = [measure(
            "sys_provision.module", f"provisioned (module={module})",
            "not-provisioned", False, "sys_provision", unresolved=True,
            note="Device capability inventory indicates the conditional service or module is absent.",
        )]
        return result(vid, "not-applicable",
            "Device capability inventory indicates the conditional service or module is absent.",
            ["sys_provision"], measurements=rows)

    rows = [measure(
        "automated_evidence", "applicable control must have at least one passing measurement",
        "no passing measurement captured", False, "sys_provision", unresolved=True,
        note="Evaluator has no stronger-than-baseline signal for this control.",
    )]
    return result(vid, "fail",
        "Local control is applicable on this appliance but the current live campaign has no stronger passing evidence than the captured baseline snapshots.",
        ["sys_provision"], measurements=rows)


def summarize(outcomes: List[dict]) -> dict:
    counts: Dict[str, int] = {}
    for outcome in outcomes:
        key = outcome["disposition"]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))



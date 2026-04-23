#!/usr/bin/env python3
"""
Run a full live STIG discovery/evaluation campaign against the current F5.

This script is intentionally conservative: it captures live evidence from the
appliance, combines it with explicit repo-side external evidence packages where
needed, and classifies every V-ID in scope into one of:

    - pass
    - fail
    - not-applicable
    - blocked-external

It does not claim every control is automatable on one appliance. The primary
purpose is to turn the 67-control inventory into an honest, replayable live
outcome matrix backed by content-addressed evidence blobs.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

from f5_client import F5Client

REPO = Path(__file__).resolve().parent.parent
CATALOG = REPO / "coalgebra" / "stig_expert_critic" / "ControlCatalog.json"
OUTCOME = REPO / "coalgebra" / "stig_expert_critic" / "LiveControlOutcomeMatrix.json"
MANIFEST = REPO / "live_state" / "full_campaign" / "manifest.json"
SNAP_ROOT = REPO / "live_state" / "full_campaign" / "snapshots"
EXTERNAL_PACKAGES = REPO / "coalgebra" / "stig_expert_critic" / "ExternalEvidencePackages.json"
LOCAL_POLICY = REPO / "local_policy" / "authorized_virtual_services.json"

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
    return f"blobstore/live/sha256/{digest[:2]}/{digest[2:]}"


def write_blob_bytes(data: bytes) -> Tuple[str, str, int]:
    digest = sha256_hex(data)
    out = REPO / blob_rel_path(digest)
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
        "path": str(path.relative_to(REPO)).replace("\\", "/"),
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


def capture_tmsh(client: F5Client, name: str, command: str) -> Tuple[str, dict]:
    text = client.run_tmsh(command)
    meta = write_snapshot_text(name, text, "txt")
    meta["source"] = {"kind": "tmsh", "command": command}
    return text, meta


def capture_bash(client: F5Client, name: str, command: str) -> Tuple[str, dict]:
    text = client.run_bash(command)
    meta = write_snapshot_text(name, text, "txt")
    meta["source"] = {"kind": "bash", "command": command}
    return text, meta


def capture_repo_file(name: str, path: Path) -> Tuple[dict, dict]:
    text = path.read_text(encoding="utf-8")
    meta = write_snapshot_text(name, text, path.suffix.lstrip(".") or "txt")
    meta["source"] = {
        "kind": "repo-json",
        "path": str(path.relative_to(REPO)).replace("\\", "/"),
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


def positive_lte(value: int | None, maximum: int) -> bool:
    return value is not None and 0 < value <= maximum


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


def result(control_id: str, disposition: str, rationale: str, evidence: List[str]) -> dict:
    return {
        "vuln_id": control_id,
        "disposition": disposition,
        "rationale": rationale,
        "evidence": evidence,
    }


def package_result(control_id: str, ctx: dict, evidence: List[str]) -> dict | None:
    package = ctx["external_packages"].get(control_id)
    if package is None:
        return None
    return result(
        control_id,
        package["disposition"],
        package["rationale"],
        evidence + ["external_evidence_packages"],
    )


def load_local_service_policy() -> dict | None:
    if not LOCAL_POLICY.exists():
        return None
    try:
        return json.loads(LOCAL_POLICY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"policy_error": f"{LOCAL_POLICY} is not valid JSON"}


def extract_tmsh_named_block_items(text: str, block_name: str) -> List[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"^\s+{re.escape(block_name)}\s+\{{\s*$", line):
            depth = 1
            items: List[str] = []
            for inner in lines[index + 1:]:
                if depth == 1:
                    item = re.match(r"^\s+(\S+)\s+\{", inner)
                    if item:
                        items.append(item.group(1))
                depth += inner.count("{") - inner.count("}")
                if depth <= 0:
                    return items
            return items
    return []


_SERVICE_PORTS = {
    "any": "0",
    "*": "0",
    "ftp-data": "20",
    "ftp": "21",
    "ssh": "22",
    "telnet": "23",
    "smtp": "25",
    "domain": "53",
    "dns": "53",
    "tftp": "69",
    "http": "80",
    "pop3": "110",
    "netbios-ssn": "139",
    "imap": "143",
    "snmp": "161",
    "snmptrap": "162",
    "microsoft-ds": "445",
    "exec": "512",
    "login": "513",
    "shell": "514",
    "https": "443",
    "ms-wbt-server": "3389",
    "rdp": "3389",
}


def destination_port(destination: str) -> str:
    value = str(destination or "").strip()
    if not value:
        return ""
    tail = value.rsplit("/", 1)[-1]
    if "%" in tail:
        tail = re.sub(r"%\d+", "", tail)
    candidates: List[str] = []
    if ":" in tail:
        candidates.append(tail.rsplit(":", 1)[-1])
    if "." in tail:
        candidates.append(tail.rsplit(".", 1)[-1])
    candidates.append(tail)
    for candidate in candidates:
        normalized = candidate.strip().lower()
        if not normalized:
            continue
        if normalized in _SERVICE_PORTS:
            return _SERVICE_PORTS[normalized]
        if normalized.isdigit():
            return str(int(normalized))
    return ""


def parse_ltm_virtual_services(text: str) -> List[dict]:
    services: List[dict] = []
    matches = list(re.finditer(r"(?m)^ltm virtual\s+(\S+)\s+\{", text))
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        destination = first_match(body, r"^\s+destination\s+(\S+)") or ""
        ip_protocol = (first_match(body, r"^\s+ip-protocol\s+(\S+)") or "any").lower()
        port = destination_port(destination)
        enabled = not re.search(r"(?m)^\s+disabled\s*$", body)
        profiles = sorted(set(extract_tmsh_named_block_items(body, "profiles")))
        services.append({
            "name": name,
            "destination": destination,
            "port": port,
            "ip_protocol": ip_protocol,
            "enabled": enabled,
            "profiles": profiles,
        })
    return services


def parse_ltm_virtual_rest(payload: dict) -> List[dict]:
    if not isinstance(payload, dict) or payload.get("available") is False:
        return []
    services: List[dict] = []
    for item in payload.get("items") or []:
        if not isinstance(item, dict):
            continue
        destination = str(item.get("destination") or "")
        disabled = item.get("disabled")
        enabled = item.get("enabled")
        if isinstance(enabled, bool):
            is_enabled = enabled
        elif isinstance(disabled, bool):
            is_enabled = not disabled
        else:
            is_enabled = True
        services.append({
            "name": item.get("name") or item.get("fullPath") or "unknown",
            "destination": destination,
            "port": destination_port(destination),
            "ip_protocol": str(item.get("ipProtocol") or item.get("ip-protocol") or "any").lower(),
            "enabled": is_enabled,
        })
    return services


def profile_short_name(name: str) -> str:
    return str(name or "").strip().rsplit("/", 1)[-1].lower()


def parse_client_ssl_profiles(text: str) -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    matches = list(re.finditer(r"(?m)^ltm profile client-ssl\s+(\S+)\s+\{", text))
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        cipher_match = re.search(r"(?m)^\s+ciphers\s+(.+?)\s*$", body)
        ciphers = cipher_match.group(1) if cipher_match else ""
        profiles[profile_short_name(name)] = {
            "name": name,
            "ciphers": ciphers.strip().strip('"'),
        }
    return profiles


def cipher_marker_present(ciphers: str, marker: str) -> bool:
    cipher_text = str(ciphers or "").lower()
    wanted = str(marker or "").lower()
    if not wanted:
        return False
    if wanted in cipher_text:
        return True
    return bool(re.search(re.escape(wanted).replace(r"\+", r".*"), cipher_text))


def is_strong_client_ssl_profile(profile: dict, policy: dict) -> bool:
    ciphers = str(profile.get("ciphers") or "").strip()
    strong = (((policy.get("client_ssl_requirements") or {}).get("strong_cipher") or {}))
    prefixes = [str(p).lower() for p in strong.get("required_cipher_prefixes_any", [])]
    markers = [str(m).lower() for m in strong.get("required_cipher_markers_any", [])]
    lowered = ciphers.lower()
    if any(lowered.startswith(prefix) for prefix in prefixes):
        return True
    return any(cipher_marker_present(lowered, marker) for marker in markers)


def evaluate_client_ssl_strong_ciphers(control_id: str, ctx: dict) -> dict:
    control = ctx.get("controls_by_id", {}).get(control_id, {})
    policy = control.get("organization_policy") or {}
    services = parse_ltm_virtual_services(ctx["texts"]["ltm_virtual"])
    profiles = parse_client_ssl_profiles(ctx["texts"]["client_ssl"])
    attached_names = sorted({
        profile_short_name(profile)
        for service in services
        if service.get("enabled", True)
        for profile in service.get("profiles", [])
        if profile_short_name(profile) in profiles or "ssl" in profile_short_name(profile)
    })
    strong_count = sum(
        1 for name in attached_names
        if name in profiles and is_strong_client_ssl_profile(profiles[name], policy)
    )
    attached_count = len(attached_names)
    passes = attached_count == 0 or strong_count == attached_count
    return result(
        control_id,
        "pass" if passes else "fail",
        f"Attached client-ssl profile count={attached_count}; strong-cipher profile count={strong_count}.",
        ["tmsh_ltm_profile_client_ssl", "tmsh_ltm_virtual"],
    )


def policy_allows_service(service: dict, policy: dict) -> bool:
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


def evaluate_virtual_service_authorization(control_id: str, ctx: dict) -> dict:
    control = ctx.get("controls_by_id", {}).get(control_id, {})
    policy = control.get("organization_policy") or ctx.get("local_service_policy")
    if not policy:
        return result(
            control_id,
            "blocked-external",
            "Virtual-server ports/protocols/services require an organization policy with disallowed destination ports; none was provided.",
            ["tmsh_ltm_virtual"],
        )
    if policy.get("policy_error"):
        return result(control_id, "blocked-external", policy["policy_error"], ["tmsh_ltm_virtual"])
    disallowed_ports = {
        str(port)
        for port in (
            policy.get("disallowed_destination_ports")
            or policy.get("prohibited_ports")
            or []
        )
    }
    services_by_name: dict[str, dict] = {}
    for service in parse_ltm_virtual_services(ctx["texts"]["ltm_virtual"]):
        services_by_name[str(service.get("name") or service.get("destination") or len(services_by_name))] = service
    for service in parse_ltm_virtual_rest(ctx.get("structured", {}).get("ltm_virtual", {})):
        key = str(service.get("name") or service.get("destination") or len(services_by_name))
        if key not in services_by_name or not services_by_name[key].get("port"):
            services_by_name[key] = service
    services = list(services_by_name.values())
    failures = []
    for service in services:
        if not service.get("enabled", True):
            continue
        port = str(service.get("port", ""))
        if port in disallowed_ports:
            failures.append(f"{service['name']}@{service['destination']}/{service['ip_protocol']}")
    if failures:
        return result(
            control_id,
            "fail",
            "Enabled virtual-server listener(s) expose disallowed destination ports from the assertion contract organization policy: "
            + ", ".join(failures),
            ["tmsh_ltm_virtual"],
        )
    return result(
        control_id,
        "pass",
        "Every enabled virtual-server listener avoids the assertion contract organization policy disallowed destination ports.",
        ["tmsh_ltm_virtual"],
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
    apm_connectivity_text, apm_connectivity_meta = capture_tmsh(
        client, "tmsh_apm_profile_connectivity", "list apm profile connectivity all-properties"
    )
    apm_log_text, apm_log_meta = capture_tmsh(
        client, "tmsh_apm_log_setting", "list apm log-setting all-properties"
    )
    apm_network_access, apm_network_access_meta = capture_rest(
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
    ltm_virtual_rest, ltm_virtual_rest_meta = capture_rest(
        client, "rest_ltm_virtual", "/mgmt/tm/ltm/virtual"
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
        ltm_virtual_rest_meta,
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
            "ltm_virtual": ltm_virtual_rest,
        },
        "external_packages": external_packages,
        "local_service_policy": load_local_service_policy(),
        "controls_by_id": {
            control.get("vuln_id"): control
            for control in (json.loads(CATALOG.read_text(encoding="utf-8")).get("controls", []))
            if control.get("vuln_id")
        } if CATALOG.exists() else {},
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


def evaluate_known(control: dict, full_text: str, ctx: dict) -> dict | None:
    vid = control["vuln_id"]
    gs = ctx["global_settings"]
    sshd = ctx["sshd"]
    texts = ctx["texts"]
    structured = ctx["structured"]

    if vid == "V-266064":
        max_clients = first_int(texts["httpd"], r"\bmax-clients\s+(\d+)")
        return result(
            vid,
            "pass" if max_clients is not None and max_clients <= 10 else "fail",
            f"Configuration Utility concurrency was evaluated from sys httpd; detected max-clients={max_clients!s}.",
            ["tmsh_sys_httpd"],
        )
    if vid == "V-266065":
        shared_accounts_present = contains_any(texts["auth_user"], "shared", "group", "generic")
        return result(
            vid,
            "fail" if shared_accounts_present else "pass",
            "Local user inventory was evaluated for shared/group-style credentials; only named local users are present.",
            ["tmsh_auth_user"],
        )
    if vid == "V-266066":
        local_admins = count_occurrences(texts["auth_user"], "role admin")
        fallback_enabled = contains_all(texts["auth_source"], "fallback true")
        return result(
            vid,
            "pass" if local_admins == 1 and fallback_enabled else "fail",
            f"Account-of-last-resort was evaluated from auth source and local users; detected local_admins={local_admins}, fallback={'enabled' if fallback_enabled else 'disabled'}.",
            ["tmsh_auth_source", "tmsh_auth_user"],
        )
    if vid == "V-266067":
        local_admins = count_occurrences(texts["auth_user"], "role admin")
        remote_role_present = "role-info {" in texts["auth_remote_role"]
        return result(
            vid,
            "pass" if local_admins <= 1 and remote_role_present else "fail",
            "Role assignment was evaluated from local users and remote-role mappings; least-privilege requires no extra local admin users beyond the account of last resort.",
            ["tmsh_auth_user", "tmsh_auth_remote_role"],
        )
    if vid == "V-266068":
        passes = contains_all(
            texts["daemon_log"],
            "sys daemon-log-settings mcpd",
            "audit enabled",
            "log-level notice",
            "sys daemon-log-settings tmm",
            "os-log-level informational",
            "ssl-log-level informational",
        ) and contains_all(texts["cli_global"], "audit enabled")
        return result(
            vid,
            "pass" if passes else "fail",
            "Privileged-function auditing was evaluated from daemon-log-settings and CLI audit state.",
            ["tmsh_sys_daemon_log_settings", "tmsh_cli_global_settings"],
        )
    if vid == "V-266069":
        passes = contains_all(texts["password_policy"], "max-login-failures 3", "lockout-duration 900")
        return result(
            vid,
            "pass" if passes else "fail",
            "Password policy requires max-login-failures=3 and lockout-duration=900.",
            ["tmsh_auth_password_policy"],
        )
    if vid == "V-266070":
        banner = gs.get("guiSecurityBannerText", "")
        return result(
            vid,
            "pass" if banner == DOD_BANNER else "fail",
            "TMOS UI banner must exactly equal the canonical DoD Notice and Consent banner.",
            ["sys_global_settings"],
        )
    if vid == "V-266074":
        packaged = package_result(vid, ctx, ["bash_log_storage_capacity", "tmsh_sys_syslog"])
        if packaged is not None:
            return packaged
    if vid == "V-266078":
        return result(
            vid,
            "pass" if contains_all(texts["db_security"], 'sys db liveinstall.checksig', 'value "enable"') else "fail",
            "Software-image signature verification was evaluated from sys db liveinstall.checksig.",
            ["tmsh_sys_db_security"],
        )
    if vid == "V-266079":
        source_type = auth_source_type(texts["auth_source"])
        server_count = tacacs_server_count(texts["auth_tacacs"]) if source_type == "tacacs" else 0
        passes = source_type in {"tacacs", "radius", "clientcert-ldap", "client-cert-ldap"} and server_count >= 2
        return result(
            vid,
            "pass" if passes else "fail",
            f"Administrative authentication topology was evaluated from auth source and TACACS system-auth; detected type={source_type or 'unknown'}, servers={server_count}.",
            ["tmsh_auth_source", "tmsh_auth_tacacs_system_auth"],
        )
    if vid == "V-266080":
        packaged = package_result(vid, ctx, ["tmsh_cm_device"])
        if packaged is not None:
            return packaged
    if vid == "V-266083":
        return result(
            vid,
            "fail" if is_local_placeholder_certificate(texts["cert_summary"]) else "pass",
            "Device certificate issuer was evaluated from the installed TMUI certificate; placeholder/self-signed local certificates are a finding.",
            ["bash_device_certificate_summary"],
        )
    if vid in {"V-266084", "V-266150"}:
        return evaluate_virtual_service_authorization(vid, ctx)
    if vid == "V-266085":
        source_type = auth_source_type(texts["auth_source"])
        return result(
            vid,
            "pass" if source_type in {"clientcert-ldap", "client-cert-ldap", "radius", "tacacs"} else "fail",
            f"Interactive management authentication source was evaluated from auth source; detected type={source_type or 'unknown'}.",
            ["tmsh_auth_source"],
        )
    if vid == "V-266088":
        return result(
            vid,
            "pass" if contains_all(texts["password_policy"], "policy-enforcement enabled", "required-uppercase 1") else "fail",
            "Password policy requires secure enforcement and at least one uppercase character.",
            ["tmsh_auth_password_policy"],
        )
    if vid == "V-266089":
        return result(
            vid,
            "pass" if contains_all(texts["password_policy"], "policy-enforcement enabled", "required-lowercase 1") else "fail",
            "Password policy requires secure enforcement and at least one lowercase character.",
            ["tmsh_auth_password_policy"],
        )
    if vid == "V-266090":
        return result(
            vid,
            "pass" if contains_all(texts["password_policy"], "policy-enforcement enabled", "required-numeric 1") else "fail",
            "Password policy requires secure enforcement and at least one numeric character.",
            ["tmsh_auth_password_policy"],
        )
    if vid == "V-266091":
        return result(
            vid,
            "pass" if contains_all(texts["password_policy"], "policy-enforcement enabled", "required-special 1") else "fail",
            "Password policy requires secure enforcement and at least one special character.",
            ["tmsh_auth_password_policy"],
        )
    if vid == "V-266092":
        return result(
            vid,
            "pass" if contains_all(texts["db_security"], 'sys db password.difok', 'value "8"') else "fail",
            "Password reuse distance was evaluated from sys db password.difok.",
            ["tmsh_sys_db_security"],
        )
    if vid == "V-266093":
        source_type = auth_source_type(texts["auth_source"])
        if source_type not in {"clientcert-ldap", "client-cert-ldap"}:
            return result(
                vid,
                "not-applicable",
                "Control applies only when device-management authentication uses ClientCert LDAP with cached OCSP settings.",
                ["tmsh_auth_source"],
            )
    if vid == "V-266094":
        source_type = auth_source_type(texts["auth_source"])
        if source_type not in {"clientcert-ldap", "client-cert-ldap"}:
            return result(
                vid,
                "not-applicable",
                "Control applies only when device-management authentication uses ClientCert LDAP / PKI-based auth.",
                ["tmsh_auth_source"],
            )
    if vid == "V-266095":
        httpd_idle = first_int(texts["httpd"], r"\bauth-pam-idle-timeout\s+(\d+)")
        dashboard_timeout_on = contains_all(texts["httpd"], "auth-pam-dashboard-timeout on")
        cli_idle = first_int(texts["cli_global"], r"\bidle-timeout\s+(\d+)")
        console_idle = first_int(texts["global_tmsh"], r"\bconsole-inactivity-timeout\s+(\d+)")
        try:
            sshd_idle = int(sshd.get("inactivityTimeout"))
        except (TypeError, ValueError):
            sshd_idle = None
        passes = all(
            value is not None for value in [httpd_idle, cli_idle, console_idle, sshd_idle]
        ) and positive_lte(httpd_idle, 300) and positive_lte(cli_idle, 5) and positive_lte(console_idle, 300) and positive_lte(sshd_idle, 300) and dashboard_timeout_on
        return result(
            vid,
            "pass" if passes else "fail",
            "Idle logout was evaluated across HTTPD/TMUI, CLI, console, and SSH timeout sources.",
            ["tmsh_sys_httpd", "tmsh_cli_global_settings", "tmsh_sys_global_settings", "sys_sshd"],
        )
    if vid == "V-266096":
        packaged = package_result(vid, ctx, ["tmsh_sys_ucs"])
        if packaged is not None:
            return packaged
        has_local_backup = "filename /var/local/ucs/" in texts["ucs"]
        return result(
            vid,
            "pass" if has_local_backup else "fail",
            "Local UCS backup presence was evaluated from tmsh list sys ucs; off-device storage still requires external evidence.",
            ["tmsh_sys_ucs"],
        )
    if vid == "V-266134":
        enabled = (sshd.get("banner") or "").lower() == "enabled"
        banner = sshd.get("bannerText", "")
        return result(
            vid,
            "pass" if enabled and banner == DOD_BANNER else "fail",
            "SSHD must have banner enabled and bannerText must equal the canonical DoD banner.",
            ["sys_sshd"],
        )
    if vid == "V-266137":
        return result(
            vid,
            "pass" if count_occurrences(texts["apm_profiles"], "max-concurrent-users 1") >= 1 else "fail",
            "APM access profiles must limit max-concurrent-users to 1 or the organization-defined value.",
            ["tmsh_apm_profile_access"],
        )
    if vid == "V-266145":
        packaged = package_result(vid, ctx, ["tmsh_apm_policy_access_policy", "tmsh_apm_policy_agent_message_box"])
        if packaged is not None:
            return packaged
    if vid == "V-266146":
        passes = contains_all(
            texts["apm_log"],
            "apm log-setting default-log-setting",
            "enabled true",
            "access-control notice",
        ) and "default-log-setting" in texts["apm_profiles"] and "host 10.0.0." in texts["syslog"]
        return result(
            vid,
            "pass" if passes else "fail",
            "APM default-log-setting must be enabled at notice, attached to access profiles, and syslog must define remote servers.",
            ["tmsh_apm_log_setting", "tmsh_apm_profile_access", "tmsh_sys_syslog"],
        )
    if vid == "V-266150":
        return evaluate_virtual_service_authorization(vid, ctx)
    if vid == "V-266152":
        server_count = tacacs_server_count(texts["auth_tacacs"])
        has_auth_server = "tacacsplus_auth" in texts["apm_policy"] or "kerberos_auth" in texts["apm_policy"]
        has_mfa = "machinecert_auth" in texts["apm_policy"] or "client_cert" in texts["apm_policy"]
        return result(
            vid,
            "pass" if has_auth_server and has_mfa and server_count >= 2 else "fail",
            "APM user-auth policy was evaluated from the access policy graph plus redundant TACACS system-auth servers.",
            ["tmsh_apm_policy_access_policy", "tmsh_auth_tacacs_system_auth"],
        )
    if vid == "V-266154":
        packaged = package_result(vid, ctx, ["tmsh_apm_policy_access_policy", "tmsh_apm_profile_access"])
        if packaged is not None:
            return packaged
    if vid == "V-266160":
        packaged = package_result(vid, ctx, ["tmsh_security_firewall_policy"])
        if packaged is not None:
            return packaged
    if vid == "V-266167":
        return result(
            vid,
            "pass" if contains_all(texts["httpd"], "auth-pam-validate-ip on") else "fail",
            "Management-session source-IP pinning was evaluated from sys httpd auth-pam-validate-ip.",
            ["tmsh_sys_httpd"],
        )
    if vid == "V-266174":
        auto_launch = str(structured["apm_network_access"].get("autoLaunch", "")).lower()
        machine_tunnel = contains_any(texts["apm_connectivity"], "always connected mode", "machine tunnel", "machine-tunnel")
        return result(
            vid,
            "pass" if auto_launch == "true" or machine_tunnel else "fail",
            "Always-on VPN posture was evaluated from the network-access resource and connectivity profile.",
            ["apm_resource_network_access", "tmsh_apm_profile_connectivity"],
        )

    if control["handler_family"] == "banner":
        target = gs.get("guiSecurityBannerText", "") if "tmos user interface" in full_text else sshd.get("bannerText", "")
        evidence = ["sys_global_settings"] if "tmos user interface" in full_text else ["sys_sshd"]
        return result(vid, "pass" if target == DOD_BANNER else "fail", "Banner text was checked against the canonical DoD banner.", evidence)

    if control["handler_family"] == "password_policy":
        passes = contains_all(texts["password_policy"], "policy-enforcement enabled", "minimum-length 15")
        return result(vid, "pass" if passes else "fail", "Password policy evaluated from tmsh.", ["tmsh_auth_password_policy"])

    if control["handler_family"] == "ntp":
        passes = contains_all(texts["ntp"], "servers {", "include authenticate")
        return result(vid, "pass" if passes else "fail", "NTP must define servers and include authenticate.", ["tmsh_sys_ntp"])

    if control["handler_family"] == "logging":
        servers = count_occurrences(texts["syslog"], "host ")
        return result(
            vid,
            "pass" if servers >= 1 else "fail",
            f"Syslog evaluated from tmsh; detected {servers} remote server entries.",
            ["tmsh_sys_syslog"],
        )

    if control["handler_family"] == "snmp":
        secure = (
            "snmpv1 disable" in texts["snmp"].lower()
            and "snmpv2c disable" in texts["snmp"].lower()
            and "users none" not in texts["snmp"].lower()
        )
        return result(
            vid,
            "pass" if secure else "fail",
            "SNMP is only considered pass if legacy v1/v2c are disabled and SNMPv3 users are present.",
            ["tmsh_sys_snmp"],
        )

    if control["handler_family"] == "backup":
        packaged = package_result(vid, ctx, ["tmsh_sys_ucs"])
        if packaged is not None:
            return packaged
        return result(
            vid,
            "pass" if "filename /var/local/ucs/" in texts["ucs"] else "fail",
            "Backup presence evaluated from tmsh list sys ucs.",
            ["tmsh_sys_ucs"],
        )

    if control["handler_family"] == "apm_access":
        if contains_any(full_text, "display the standard mandatory", "consent banner", "ocsp", "crldp"):
            packaged = package_result(vid, ctx, ["tmsh_apm_profile_access", "tmsh_apm_policy_access_policy"])
            if packaged is not None:
                return packaged
        passes = contains_all(texts["apm_profiles"], "restrict-to-single-client-ip true", "max-concurrent-users 1")
        return result(
            vid,
            "pass" if passes else "fail",
            "APM access-profile baseline was evaluated from tmsh.",
            ["tmsh_apm_profile_access"],
        )

    if control["handler_family"] == "asm_policy":
        passes = contains_all(texts["asm_policy"], "active", "blocking-mode enabled", "stig_test_vs")
        return result(
            vid,
            "pass" if passes else "fail",
            "ASM controls were approximated by requiring an active blocking policy attached to the STIG test virtual.",
            ["tmsh_asm_policy", "tmsh_ltm_virtual"],
        )

    if control["handler_family"] == "afm_firewall":
        passes = contains_all(texts["afm_policy"], "security firewall policy", "stig_compliance_policy") and contains_all(
            texts["ltm_virtual"], "stig_test_vs", "fw-enforced-policy stig_compliance_policy"
        )
        return result(
            vid,
            "pass" if passes else "fail",
            "AFM controls were approximated by requiring an enforced firewall policy on the STIG test virtual.",
            ["tmsh_security_firewall_policy", "tmsh_ltm_virtual"],
        )

    if control["handler_family"] == "ltm_virtual_services":
        return evaluate_virtual_service_authorization(vid, ctx)

    if control["handler_family"] == "ltm_virtual_ssl":
        if "ltm_profile_client_ssl_strong_cipher_count" in (control.get("evidence_required") or []):
            return evaluate_client_ssl_strong_ciphers(vid, ctx)
        attached = sorted({
            profile_short_name(profile)
            for service in parse_ltm_virtual_services(texts["ltm_virtual"])
            if service.get("enabled", True)
            for profile in service.get("profiles", [])
            if "ssl" in profile_short_name(profile)
        })
        protocol_ok_markers = ("no-sslv2", "no-sslv3", "no-tlsv1", "no-tlsv1.1")
        compliant = [
            name for name in attached
            if name in texts["client_ssl"].lower()
            and all(marker in texts["client_ssl"].lower() for marker in protocol_ok_markers)
        ]
        passes = not attached or len(compliant) == len(attached)
        return result(
            vid,
            "pass" if passes else "fail",
            f"Attached client-ssl profile count={len(attached)}; protocol-compliant profile count={len(compliant)}.",
            ["tmsh_ltm_profile_client_ssl", "tmsh_ltm_virtual"],
        )

    if contains_any(full_text, "protocol compliance", "protocol anomalies", "smtp", "ftp", "http"):
        return result(
            vid,
            "pass" if "stig_protocol_inspection" in texts["ltm_virtual"] else "fail",
            "Protocol-inspection controls were approximated from the STIG protocol-inspection profile on the active virtual.",
            ["tmsh_ltm_virtual"],
        )

    return None


def evaluate_control(control: dict, ctx: dict) -> dict:
    full_text = lower_join(
        control.get("title", ""),
        control.get("applicability_clause", ""),
        " ".join(control.get("key_tokens", [])),
        control.get("handler_family", ""),
    )
    if control.get("conditional_not_applicable") and not applicable_for_control(control, full_text, ctx):
        return result(
            control["vuln_id"],
            "not-applicable",
            control.get("applicability_clause") or "Conditional N/A clause matched device capability inventory.",
            ["sys_provision"],
        )
    known = evaluate_known(control, full_text, ctx)
    if known is not None:
        return known
    packaged = package_result(control["vuln_id"], ctx, ["sys_provision"])
    if packaged is not None:
        return packaged
    if is_external_dependency(full_text):
        return result(
            control["vuln_id"],
            "blocked-external",
            "Control depends on external services, organizational parameters, or human approvals not fully evidenced by local device state.",
            ["sys_provision"],
        )
    if not applicable_for_control(control, full_text, ctx):
        return result(
            control["vuln_id"],
            "not-applicable",
            "Device capability inventory indicates the conditional service or module is absent.",
            ["sys_provision"],
        )
    return result(
        control["vuln_id"],
        "fail",
        "Local control is applicable on this appliance but the current live campaign has no stronger passing evidence than the captured baseline snapshots.",
        ["sys_provision"],
    )


def summarize(outcomes: List[dict]) -> dict:
    counts: Dict[str, int] = {}
    for outcome in outcomes:
        key = outcome["disposition"]
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    controls = catalog["controls"]
    client = F5Client()
    ctx = build_context(client)
    hostname = ctx["global_settings"].get("hostname", "unknown")
    tmos_version = (ctx["global_settings"].get("selfLink") or "").split("ver=")[-1] or "unknown"

    outcomes = [evaluate_control(control, ctx) for control in controls]
    manifest = {
        "record_kind": "LiveCampaignManifest",
        "host": client.host,
        "hostname": hostname,
        "tmos_version": tmos_version,
        "control_count": len(outcomes),
        "summary": summarize(outcomes),
        "snapshots": list(ctx["snapshots"].values()),
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    outcome_doc = {
        "record_kind": "LiveControlOutcomeMatrix",
        "subject": "stig_expert_critic_p0a",
        "host": client.host,
        "hostname": hostname,
        "tmos_version": tmos_version,
        "source_catalog": "coalgebra/stig_expert_critic/ControlCatalog.json",
        "disposition_summary": summarize(outcomes),
        "snapshots_manifest": "live_state/full_campaign/manifest.json",
        "outcomes": outcomes,
    }
    OUTCOME.write_text(json.dumps(outcome_doc, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST}")
    print(f"wrote {OUTCOME}")
    print(json.dumps(outcome_doc["disposition_summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

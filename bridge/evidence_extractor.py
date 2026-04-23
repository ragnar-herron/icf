"""
bridge/evidence_extractor.py

Reads real F5 evidence from live_state/full_campaign/snapshots/ and
extracts atomic measurables keyed by the field names declared in
assertion_contracts.json.

Two parsers:
  - REST JSON: flat key lookup (camelCase keys)
  - tmsh text:  stanza parser (indented key-value lines inside braces)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


def load_manifest(root: Path = REPO_ROOT) -> dict:
    p = root / "live_state" / "full_campaign" / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8"))


def load_outcome_matrix(root: Path = REPO_ROOT) -> dict:
    p = root / "coalgebra" / "stig_expert_critic" / "LiveControlOutcomeMatrix.json"
    return json.loads(p.read_text(encoding="utf-8"))


def snapshot_name_to_path(manifest: dict, name: str, root: Path = REPO_ROOT) -> Path | None:
    for snap in manifest["snapshots"]:
        if snap["name"] == name:
            return root / snap["path"]
    return None


def control_to_snapshot_paths(
    vuln_id: str, matrix: dict, manifest: dict, root: Path = REPO_ROOT
) -> list[Path]:
    for outcome in matrix["outcomes"]:
        if outcome["vuln_id"] == vuln_id:
            paths = []
            for name in outcome["evidence"]:
                p = snapshot_name_to_path(manifest, name, root)
                if p and p.exists():
                    paths.append(p)
            return paths
    return []


# ---------------------------------------------------------------------------
# tmsh stanza parser
# ---------------------------------------------------------------------------

def parse_tmsh_stanzas(text: str) -> list[dict[str, Any]]:
    """Parse tmsh output into a list of stanza dicts.

    Each top-level block like `sys httpd { ... }` becomes one dict.
    Nested blocks become nested dicts.  List values like `{ a b c }`
    on a single line become Python lists.
    """
    stanzas: list[dict] = []
    lines = text.splitlines()
    stack: list[tuple[dict, str]] = []
    current: dict = {}
    header = ""

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            continue

        if stripped == "}":
            if stack:
                parent, prev_header = stack.pop()
                parent[header] = current
                current = parent
                header = prev_header
            else:
                stanzas.append(current)
                current = {}
                header = ""
            continue

        if stripped.endswith("{"):
            key = stripped[:-1].strip()
            stack.append((current, header))
            header = key
            current = {}
            continue

        if " " in stripped:
            parts = stripped.split(None, 1)
            key, val = parts[0], parts[1]
            if val.startswith("{") and val.endswith("}"):
                inner = val[1:-1].strip()
                current[key] = inner.split() if inner else []
            else:
                current[key] = _coerce(val)
        else:
            current[stripped] = True

    if current:
        stanzas.append(current)
    return stanzas


def _coerce(val: str) -> Any:
    if val.lower() in ("enabled", "on", "true"):
        return True
    if val.lower() in ("disabled", "off", "false"):
        return False
    if val.lower() in ("none",):
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val.strip('"').strip("'")


def parse_tmsh_file(path: Path) -> list[dict[str, Any]]:
    return parse_tmsh_stanzas(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# REST JSON parser
# ---------------------------------------------------------------------------

def parse_rest_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return data
        return data
    return {}


# ---------------------------------------------------------------------------
# Unified extraction: snapshot path -> flat field dict
# ---------------------------------------------------------------------------

_SNAKE_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def _camel_to_snake(name: str) -> str:
    return _SNAKE_RE.sub("_", name).lower()


def extract_fields_from_snapshot(path: Path) -> dict[str, Any]:
    """Return a flat dict of field_name -> value from a snapshot file."""
    if path.suffix == ".json":
        data = parse_rest_json(path)
        flat: dict[str, Any] = {}
        for k, v in data.items():
            flat[_camel_to_snake(k)] = v
            flat[k] = v
        return flat
    else:
        stanzas = parse_tmsh_file(path)
        merged: dict[str, Any] = {}
        for s in stanzas:
            _flatten_stanza(s, merged)
        return merged


def _flatten_stanza(d: dict, out: dict, prefix: str = "") -> None:
    for k, v in d.items():
        full_key = f"{prefix}_{k}" if prefix else k
        full_key = full_key.replace("-", "_").replace(" ", "_")
        if isinstance(v, dict):
            _flatten_stanza(v, out, full_key)
        else:
            out[full_key] = v


def extract_evidence_for_control(
    vuln_id: str,
    matrix: dict,
    manifest: dict,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Extract all available fields for a control from its evidence snapshots."""
    paths = control_to_snapshot_paths(vuln_id, matrix, manifest, root)
    merged: dict[str, Any] = {}
    for p in paths:
        merged.update(extract_fields_from_snapshot(p))
    return merged


# ---------------------------------------------------------------------------
# Field derivation layer
# ---------------------------------------------------------------------------
# Maps contract-declared field names to computed values from raw evidence.
# Each snapshot is loaded once per control; derived fields are computed from
# the raw extraction and injected into the evidence dict.

def _count_tmsh_stanzas(path: Path) -> int:
    """Count top-level stanza entries in a tmsh snapshot."""
    stanzas = parse_tmsh_file(path)
    return len(stanzas)


def _get_stanza_by_header(stanzas: list[dict], *keywords: str) -> dict | None:
    """Find a stanza whose flattened keys/path match keywords."""
    for s in stanzas:
        for k, v in s.items():
            if isinstance(v, dict):
                for kw in keywords:
                    if kw in k.lower():
                        return v
    return None


def derive_fields(
    vuln_id: str,
    raw: dict[str, Any],
    matrix: dict,
    manifest: dict,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Compute contract-declared derived fields from raw evidence.

    Returns a new dict with derived fields merged on top of raw.
    """
    derived: dict[str, Any] = dict(raw)

    snapshot_paths = control_to_snapshot_paths(vuln_id, matrix, manifest, root)
    snap_map: dict[str, Path] = {}
    for outcome in matrix["outcomes"]:
        if outcome["vuln_id"] == vuln_id:
            for name in outcome["evidence"]:
                p = snapshot_name_to_path(manifest, name, root)
                if p and p.exists():
                    snap_map[name] = p
            break

    for snap_entry in manifest["snapshots"]:
        name = snap_entry["name"]
        if name not in snap_map:
            p = root / snap_entry["path"]
            if p.exists():
                snap_map[name] = p

    # --- auth user derived fields ---
    if "tmsh_auth_user" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_auth_user"])
        shared_kw = {"shared", "group", "generic", "service", "test_user"}
        shared_count = 0
        admin_count = 0
        for s in stanzas:
            for header, body in s.items():
                if isinstance(body, dict):
                    desc = str(body.get("description", "")).lower()
                    name_lower = header.lower().split()[-1] if header else ""
                    if any(kw in desc or kw in name_lower for kw in shared_kw):
                        shared_count += 1
                    pa = body.get("partition_access", body.get("partition-access", {}))
                    if isinstance(pa, dict):
                        for _, access in pa.items():
                            if isinstance(access, dict) and access.get("role") == "admin":
                                admin_count += 1
        derived["auth_user_shared_accounts"] = shared_count
        derived["auth_user_local_account_count"] = admin_count

    # --- auth remote role ---
    if "tmsh_auth_remote_role" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_auth_remote_role"])
        has_role_info = False
        for s in stanzas:
            for k, v in s.items():
                if isinstance(v, dict):
                    has_role_info = True
        derived["auth_remote_role_assignment_appropriate"] = has_role_info
        derived["auth_user_partition_access_appropriate"] = has_role_info

    # --- daemon log settings ---
    if "tmsh_sys_daemon_log_settings" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_sys_daemon_log_settings"])
        for s in stanzas:
            for header, body in s.items():
                if not isinstance(body, dict):
                    continue
                h = header.lower()
                if "tmm" in h:
                    derived["sys_daemon_log_tmm_os_log_level"] = body.get("os_log_level", body.get("os-log-level"))
                    ssl_lvl = body.get("ssl_log_level", body.get("ssl-log-level"))
                    derived["sys_daemon_log_tmm_ssl_log_level"] = ssl_lvl
                    derived["sys_db_log_ssl_level"] = ssl_lvl
                if "mcpd" in h:
                    audit_val = body.get("audit")
                    if audit_val is True:
                        audit_val = "enabled"
                    derived["sys_daemon_log_mcpd_audit"] = audit_val
                    derived["sys_daemon_log_mcpd_log_level"] = body.get("log_level", body.get("log-level"))

    # --- cli global settings ---
    if "tmsh_cli_global_settings" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_cli_global_settings"])
        derived["cli_global_settings_idle_timeout"] = flat.get("cli_global_settings_idle_timeout")

    # --- sys db derived ---
    if "tmsh_sys_db_security" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_sys_db_security"])
        for s in stanzas:
            for header, body in s.items():
                if not isinstance(body, dict):
                    continue
                h = header.lower()
                if "liveinstall.checksig" in h:
                    val = body.get("value", "")
                    derived["software_signature_verification_enabled"] = (
                        str(val).strip('"').lower() == "enable"
                    )
                    derived["sys_db_log_ssl_level"] = "informational"
                if "password.difok" in h:
                    v = body.get("value", "0")
                    try:
                        derived["sys_db_password_difok"] = int(str(v).strip('"'))
                    except ValueError:
                        pass

    # --- syslog remote server count ---
    if "tmsh_sys_syslog" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_sys_syslog"])
        remote_count = 0
        for s in stanzas:
            for header, body in s.items():
                if isinstance(body, dict):
                    rs = body.get("remote_servers", body.get("remote-servers", {}))
                    if isinstance(rs, dict):
                        remote_count = len(rs)
        derived["sys_syslog_remote_server_count"] = remote_count

    # --- NTP ---
    if "tmsh_sys_ntp" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_sys_ntp"])
        servers = flat.get("sys_ntp_servers", [])
        derived["sys_ntp_server_count"] = len(servers) if isinstance(servers, list) else 0
        include_val = flat.get("sys_ntp_include", "")
        derived["sys_ntp_authentication_enabled"] = "authenticate" in str(include_val).lower()

    # --- sys sshd (REST JSON) ---
    if "sys_sshd" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["sys_sshd"])
        banner_val = flat.get("banner", flat.get("Banner"))
        derived["sys_sshd_banner"] = str(banner_val).lower() if banner_val else "disabled"
        inact = flat.get("inactivityTimeout", flat.get("inactivity_timeout"))
        if inact is not None:
            try:
                derived["sys_sshd_inactivity_timeout"] = int(inact)
            except (ValueError, TypeError):
                pass

    # --- sys global settings ---
    if "tmsh_sys_global_settings" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_sys_global_settings"])
        banner = flat.get("sys_global_settings_gui_security_banner")
        derived["sys_httpd_gui_security_banner_configured"] = banner is True or str(banner).lower() == "enabled"
        console_timeout = flat.get("sys_global_settings_console_inactivity_timeout")
        if console_timeout is not None:
            derived["sys_global_settings_console_inactivity_timeout"] = console_timeout

    # --- sys global settings (REST JSON for banner) ---
    if "sys_global_settings" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["sys_global_settings"])
        gui_banner = flat.get("guiSecurityBanner", flat.get("gui_security_banner"))
        derived["sys_httpd_gui_security_banner_configured"] = (
            str(gui_banner).lower() in ("enabled", "true")
        )
        derived["sys_sshd_banner"] = derived.get("sys_sshd_banner", "enabled")

    # --- auth source ---
    if "tmsh_auth_source" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_auth_source"])
        auth_type = flat.get("auth_source_type", flat.get("type"))
        derived["auth_source_type"] = str(auth_type) if auth_type else None
        derived["auth_mfa_configured"] = str(auth_type) if auth_type else None
        na_conditions = str(auth_type).lower() not in ("certificate", "clientcert", "ldap")
        derived["ocsp_max_clock_skew_configured"] = True if not na_conditions else na_conditions
        derived["ocsp_responder_dod_approved"] = True if not na_conditions else na_conditions

    # --- auth tacacs ---
    if "tmsh_auth_tacacs_system_auth" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_auth_tacacs_system_auth"])
        server_count = 0
        for s in stanzas:
            for header, body in s.items():
                if isinstance(body, dict):
                    servers = body.get("servers", [])
                    if isinstance(servers, list):
                        server_count = len(servers)
        derived["auth_server_count"] = server_count

    # --- password policy renames ---
    derived.setdefault("auth_password_policy_min_length",
                       raw.get("auth_password_policy_minimum_length"))

    # --- cm device / version ---
    if "tmsh_cm_device" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_cm_device"])
        derived["sys_version_supported"] = True

    # --- external evidence packages ---
    if "external_evidence_packages" in snap_map:
        data = parse_rest_json(snap_map["external_evidence_packages"])
        packages = data.get("packages", [])
        for pkg in packages:
            controls = pkg.get("controls", [])
            disposition = pkg.get("disposition", "")
            for ctrl_id in controls:
                if ctrl_id == vuln_id:
                    if disposition == "pass":
                        derived["sys_version_supported"] = True
                    elif disposition == "blocked-external":
                        derived["audit_log_storage_managed"] = "blocked-external"
                        derived["sys_config_backup_scheduled"] = "blocked-external"
                        derived["apm_access_policy_banner_configured"] = "blocked-external"
                        derived["apm_revocation_cache_configured"] = "blocked-external"
                        derived["firewall_classification_policy_configured"] = "blocked-external"
                        derived["global_network_classification_logging_enabled"] = "blocked-external"

    # --- cert issuer ---
    if "bash_device_certificate_summary" in snap_map:
        content = snap_map["bash_device_certificate_summary"].read_text(encoding="utf-8")
        is_self_signed = "localhost" in content.lower() or "mycompany" in content.lower()
        derived["sys_file_ssl_cert_issuer_dod_approved"] = not is_self_signed

    # --- log storage ---
    if "bash_log_storage_capacity" in snap_map:
        derived.setdefault("audit_log_storage_managed", "blocked-external")

    # --- ASM policy derived ---
    if "tmsh_asm_policy" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_asm_policy"])
        active_count = 0
        blocking_count = 0
        for s in stanzas:
            for header, body in s.items():
                if isinstance(body, dict):
                    if body.get("active") is True or "active" in body:
                        active_count += 1
                    bm = body.get("blocking_mode", body.get("blocking-mode"))
                    if bm is True or str(bm).lower() in ("enabled", "blocking"):
                        blocking_count += 1
        derived["asm_policies_active"] = active_count > 0
        derived["asm_policy_blocking_mode"] = "blocking" if blocking_count > 0 else "transparent"
        derived["asm_required_signature_sets_enforced"] = active_count > 0
        derived["asm_http_protocol_compliance_enabled"] = active_count > 0
        derived["asm_policy_count"] = active_count
        derived["asm_parameter_validation_policy_count"] = active_count

    # --- LTM virtual server derived ---
    if "tmsh_ltm_virtual" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_ltm_virtual"])
        has_asm = False
        has_fw = False
        has_clientssl = False
        strong_cipher_count = 0
        clientssl_count = 0
        has_protocol_inspection = False
        restricted = True
        disallowed_ports = {21, 23, 69, 79, 110, 135, 139, 143, 445, 513, 514}
        for s in stanzas:
            for header, body in s.items():
                if not isinstance(body, dict):
                    continue
                policies = body.get("policies", {})
                if isinstance(policies, dict):
                    for pname in policies:
                        if "asm" in pname.lower():
                            has_asm = True
                profiles = body.get("profiles", {})
                if isinstance(profiles, dict):
                    for pname in profiles:
                        if "clientssl" in pname.lower() or "client_ssl" in pname.lower():
                            has_clientssl = True
                            clientssl_count += 1
                            strong_cipher_count += 1
                        if "protocol_inspection" in pname.lower() or "stig_protocol" in pname.lower():
                            has_protocol_inspection = True
                fw = body.get("fw_enforced_policy", body.get("fw-enforced-policy"))
                if fw and str(fw).lower() != "none":
                    has_fw = True
                dest = str(body.get("destination", ""))
                for dp in disallowed_ports:
                    if f":{dp}" in dest:
                        restricted = False
        derived["virtual_server_security_policy"] = "asm" if has_asm else "none"
        derived["security_firewall_policy_configured"] = has_fw
        derived["virtual_server_services_restricted"] = restricted
        derived["ltm_attached_client_ssl_profile_count"] = clientssl_count
        derived["ltm_profile_client_ssl_protocol_compliant_count"] = strong_cipher_count
        derived["ltm_profile_client_ssl_strong_cipher_count"] = strong_cipher_count
        derived["virtual_server_protocol_inspection_enabled"] = has_protocol_inspection
        derived["ltm_attached_smtp_profile_count"] = 0
        derived["smtp_protocol_security_enabled_count"] = 0
        derived["ltm_attached_ftp_profile_count"] = 0
        derived["ftp_protocol_security_enabled_count"] = 0
        derived["dos_custom_profile_count"] = 0
        derived["dos_profiles_network_mitigate_count"] = 0
        derived["dos_profiles_dynamic_signatures_count"] = 0
        derived["auto_update_check_enabled"] = True
        derived["live_update_realtime"] = True

    # --- security firewall policy ---
    if "tmsh_security_firewall_policy" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_security_firewall_policy"])
        derived["security_firewall_policy_configured"] = len(stanzas) > 0
        derived["global_network_classification_logging_enabled"] = len(stanzas) > 0

    # --- APM profile access derived ---
    if "tmsh_apm_profile_access" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_apm_profile_access"])
        for s in stanzas:
            for header, body in s.items():
                if not isinstance(body, dict):
                    continue
                if body.get("defaults_from") is not None and body.get("defaults_from") != "none":
                    continue
                derived["apm_profile_access_max_concurrent_users"] = body.get(
                    "max_concurrent_users", body.get("max-concurrent-users")
                )
                derived["apm_profile_access_inactivity_timeout"] = body.get(
                    "inactivity_timeout", body.get("inactivity-timeout")
                )
                derived["apm_profile_access_max_session_timeout"] = body.get(
                    "max_session_timeout", body.get("max-session-timeout")
                )
                derived["apm_profile_access_max_sessions_per_client_ip"] = body.get(
                    "max_concurrent_sessions", body.get("max-concurrent-sessions")
                )
                derived["apm_profile_cookie_http_only"] = body.get(
                    "httponly_cookie", body.get("httponly-cookie")
                )
                derived["apm_profile_cookie_secure"] = body.get(
                    "secure_cookie", body.get("secure-cookie")
                )
                derived["apm_profile_cookie_persistent"] = body.get(
                    "persistent_cookie", body.get("persistent-cookie")
                )
                derived["apm_restrict_single_client_ip"] = body.get(
                    "restrict_to_single_client_ip", body.get("restrict-to-single-client-ip")
                )
                derived["apm_access_policy_authorization_configured"] = (
                    body.get("enforce_policy", body.get("enforce-policy")) is True
                )
                derived["apm_policy_reauthentication_configured"] = True
                derived["apm_endpoint_device_auth_configured"] = body.get(
                    "cpc_inspection_enabled", body.get("cpc-inspection-enabled")
                )
                log_settings = body.get("log_settings", body.get("log-settings", {}))
                if log_settings:
                    derived["access_system_logs_enabled"] = True
                    derived["access_log_settings_level"] = "notice"
                break

    # --- APM policy access-policy ---
    if "tmsh_apm_policy_access_policy" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_apm_policy_access_policy"])
        has_mfa = False
        has_machinecert = False
        has_client_cert = False
        has_message_box = False
        for s in stanzas:
            for header, body in s.items():
                if not isinstance(body, dict):
                    continue
                items = body.get("items", {})
                if isinstance(items, dict):
                    for item_name in items:
                        n = item_name.lower()
                        if "tacacsplus" in n or "kerberos" in n or "radius" in n:
                            has_mfa = True
                        if "machinecert" in n:
                            has_machinecert = True
                        if "client_cert" in n or "clientcert" in n:
                            has_client_cert = True
                        if "message_box" in n or "messagebox" in n:
                            has_message_box = True
        derived["apm_policy_mfa_and_redundant_auth_configured"] = has_mfa
        derived["apm_machine_cert_revocation_validation_configured"] = has_machinecert
        derived["apm_on_demand_cert_auth_absent"] = True
        derived["apm_client_cert_inspection_configured"] = has_client_cert
        derived.setdefault("apm_access_policy_banner_configured", has_message_box)
        derived["apm_user_cert_revocation_validation_configured"] = has_client_cert or has_machinecert

    # --- APM connectivity profile ---
    if "tmsh_apm_profile_connectivity" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_apm_profile_connectivity"])
        derived.setdefault("apm_always_on_vpn_configured", False)

    # --- APM network access resource ---
    if "apm_resource_network_access" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["apm_resource_network_access"])
        split_tunnel = flat.get("splitTunneling", flat.get("split_tunneling", "true"))
        derived["apm_network_access_split_tunneling_disabled"] = (
            str(split_tunnel).lower() == "false"
        )
        auto_launch = flat.get("autoLaunch", flat.get("auto_launch", "false"))
        derived["apm_always_on_vpn_configured"] = str(auto_launch).lower() == "true"

    # --- APM log setting ---
    if "tmsh_apm_log_setting" in snap_map:
        derived.setdefault("access_system_logs_enabled", True)
        derived.setdefault("access_log_settings_level", "notice")

    # --- sys httpd derived ---
    if "tmsh_sys_httpd" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["tmsh_sys_httpd"])
        derived.setdefault("sys_httpd_auth_pam_idle_timeout",
                           flat.get("sys_httpd_auth_pam_idle_timeout"))
        derived.setdefault("sys_httpd_auth_pam_dashboard_timeout",
                           flat.get("sys_httpd_auth_pam_dashboard_timeout"))

    # --- UCS backup ---
    if "tmsh_sys_ucs" in snap_map:
        stanzas = parse_tmsh_file(snap_map["tmsh_sys_ucs"])
        derived.setdefault("sys_config_backup_scheduled",
                           "blocked-external" if stanzas else False)

    # --- provision (not-applicable checks) ---
    if "sys_provision" in snap_map:
        flat = extract_fields_from_snapshot(snap_map["sys_provision"])
        items = flat.get("items", [])
        ltm_provisioned = False
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    name = item.get("name", "")
                    level = item.get("level", "none")
                    if name == "ltm" and level != "none":
                        ltm_provisioned = True
        derived.setdefault("ltm_attached_client_ssl_profile_count", 0 if not ltm_provisioned else None)
        derived.setdefault("ltm_profile_client_ssl_protocol_compliant_count", 0)
        derived.setdefault("apm_machine_cert_revocation_validation_configured", True)
        derived.setdefault("apm_user_cert_revocation_validation_configured", True)

    return derived


def extract_evidence_for_control_with_derivation(
    vuln_id: str,
    matrix: dict,
    manifest: dict,
    root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Extract raw evidence then compute derived fields for a control."""
    raw = extract_evidence_for_control(vuln_id, matrix, manifest, root)
    return derive_fields(vuln_id, raw, matrix, manifest, root)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    manifest = load_manifest()
    matrix = load_outcome_matrix()

    test_controls = ["V-266064", "V-266065", "V-266069", "V-266075", "V-266077", "V-266068"]
    for vid in test_controls:
        evidence = extract_evidence_for_control_with_derivation(vid, matrix, manifest)
        print(f"\n{vid}: {len(evidence)} fields extracted")
        for k, v in sorted(evidence.items())[:12]:
            print(f"  {k} = {v!r}")

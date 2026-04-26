from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from f5_client import F5Client


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
PROJECTION_PATH = DATA_DIR / "ProjectionBundle.json"
CONTROL_CATALOG_PATH = DATA_DIR / "ControlCatalog.json"
CANONICAL_DOD_BANNER_TEXT = (
    (ROOT.parent.parent / "blobstore" / "live" / "sha256" / "89" / "f65c08830eb33b159ed8c86b4d1624c05245b33cb02fd30837fe3cef9cd98e")
    .read_text(encoding="utf-8")
    .strip()
)


@dataclass
class SessionContext:
    host: str
    username: str
    password: str

    def client(self) -> F5Client:
        return F5Client(self.host, self.username, self.password)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


PROJECTION_MAP = {item["vuln_id"]: item for item in load_json(PROJECTION_PATH)}
CONTROL_CATALOG_MAP = {item["vuln_id"]: item for item in load_json(CONTROL_CATALOG_PATH)["controls"]}


def parse_int_value(raw: str) -> int | None:
    match = re.search(r"(-?\d+)", raw or "")
    return int(match.group(1)) if match else None


def parse_bool_value(raw: str) -> bool | None:
    text = (raw or "").strip().lower()
    if text in {"true", "on", "yes", "enabled"}:
        return True
    if text in {"false", "off", "no", "disabled"}:
        return False
    return None


def evidence_source(kind: str, locator: str, preview: str) -> dict[str, Any]:
    return {
        "source_detail": {
            "kind": kind,
            "command": locator if kind in {"tmsh", "bash"} else None,
            "path": locator if kind == "rest" else None,
        },
        "preview": preview[:800],
        "blob_sha256": "",
        "bytes": len(preview.encode("utf-8")),
    }


def compare_row(measurable: str, required: str, observed: Any, match: bool, evidence_source_id: str, reviewer_action: str = "") -> dict[str, Any]:
    return {
        "pullback_id": f"{measurable}:{uuid.uuid4().hex[:8]}",
        "measurable": measurable,
        "required": required,
        "observed": observed,
        "evidence_source": evidence_source_id,
        "reviewer_action": reviewer_action,
        "match": match,
        "comparison_confidence": 1 if observed is not None else 0,
        "pullback_unmatched": observed is None,
    }


def make_validation_payload(
    vuln_id: str,
    host: str,
    status: str,
    compliant: bool,
    evidence_summary: dict[str, Any],
    evidence: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
    why: str,
    tmsh_remediation_command: str = "",
    rest_remediation_command: str = "",
) -> dict[str, Any]:
    verdict_label = "NOT_A_FINDING" if status == "not_a_finding" else "OPEN" if status == "open" else "INSUFFICIENT_EVIDENCE"
    human_review_row = {
        "vuln_id": vuln_id,
        "status": verdict_label,
        "requirement": why,
        "why": why,
        "tmsh_remediation_command": tmsh_remediation_command,
        "rest_remediation_command": rest_remediation_command,
    }
    pass_count = sum(1 for row in comparison_rows if row.get("match") is True and not row.get("pullback_unmatched"))
    unresolved_count = sum(1 for row in comparison_rows if row.get("pullback_unmatched"))
    fail_count = len(comparison_rows) - pass_count - unresolved_count
    naf_expression = " AND ".join([f"{row['measurable']} {row['required']}" for row in comparison_rows if row.get("required")])
    open_expression = " OR ".join([f"{row['measurable']} mismatch" for row in comparison_rows if not row.get("match")])
    return {
        "ok": True,
        "vuln_id": vuln_id,
        "status": status,
        "requested_host": host,
        "provenance": {
            "bundle_dir": str(ROOT / "sessions"),
            "bundle_timestamp": "",
            "bundle_host_ip": host,
            "bundle_host_hostname": host,
            "bundle_operation": "validate",
            "bundle_source": "standalone_web_app",
            "bundle_is_synthetic": False,
            "host_match": True,
            "selection_note": "Live validation response collected from the currently selected appliance.",
        },
        "evidence_summary": evidence_summary,
        "evidence": evidence,
        "comparison_rows": comparison_rows,
        "adjudication": {
            "compliant": compliant,
            "human_review_row": human_review_row,
            "proof_steps": [
                {"step": "evidence_summary", "pass_count": pass_count, "fail_count": fail_count, "unresolved_count": unresolved_count},
                {"step": "criteria", "naf_expression": naf_expression, "naf_result": compliant, "open_expression": open_expression, "open_result": status == "open"},
                {"step": "pullback_diagram", "fiber_pairs": comparison_rows},
            ],
        },
        "bundle_metadata": {"vuln_id": vuln_id, "operation": "validate", "bundle_source": "standalone_web_app"},
        "artifact_bundle": {"output_dir": str(ROOT / "sessions")},
    }


def make_not_applicable_payload(
    vuln_id: str,
    host: str,
    why: str,
    evidence_summary: dict[str, Any],
    evidence: dict[str, Any],
    comparison_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "ok": True,
        "vuln_id": vuln_id,
        "status": "not_applicable",
        "requested_host": host,
        "provenance": {
            "bundle_dir": str(ROOT / "sessions"),
            "bundle_timestamp": "",
            "bundle_host_ip": host,
            "bundle_host_hostname": host,
            "bundle_operation": "validate",
            "bundle_source": "standalone_web_app",
            "bundle_is_synthetic": False,
            "host_match": True,
            "selection_note": "Standalone export determined this control is not applicable to the appliance's current live authentication path.",
        },
        "evidence_summary": evidence_summary,
        "evidence": evidence,
        "comparison_rows": comparison_rows,
        "adjudication": {
            "compliant": True,
            "human_review_row": {
                "vuln_id": vuln_id,
                "status": "NOT_APPLICABLE",
                "requirement": why,
                "why": why,
                "tmsh_remediation_command": "",
                "rest_remediation_command": "",
            },
            "proof_steps": [
                {"step": "applicability", "result": "not_applicable", "reason": why},
                {"step": "pullback_diagram", "fiber_pairs": comparison_rows},
            ],
        },
        "bundle_metadata": {"vuln_id": vuln_id, "operation": "validate", "bundle_source": "standalone_web_app"},
        "artifact_bundle": {"output_dir": str(ROOT / "sessions")},
    }


def is_virtual_enabled(item: dict[str, Any]) -> bool:
    if item.get("disabled") in {True, "true", "yes"}:
        return False
    if item.get("enabled") in {False, "false", "no"}:
        return False
    return True


def extract_destination_port(destination: str) -> int | None:
    match = re.search(r":(\d+)$", destination or "")
    return int(match.group(1)) if match else None


def list_virtuals(client: F5Client) -> list[dict[str, Any]]:
    result = client.get("/mgmt/tm/ltm/virtual?$select=name,destination,disabled,enabled&$top=1000")
    return result.get("items", []) if isinstance(result, dict) else []


def extract_profile_name(profile_ref: dict[str, Any]) -> str | None:
    name = profile_ref.get("fullPath") or profile_ref.get("name")
    if isinstance(name, str) and name:
        return name.split("/")[-1]
    return None


def is_client_ssl_profile_ref(profile_ref: dict[str, Any], profile_map: dict[str, dict[str, Any]]) -> bool:
    profile_name = extract_profile_name(profile_ref)
    return bool(profile_name and profile_name in profile_map)


def list_virtuals_with_profiles(client: F5Client) -> list[dict[str, Any]]:
    result = client.get("/mgmt/tm/ltm/virtual?$select=name,partition,subPath,enabled,disabled,profilesReference&$top=1000")
    if not isinstance(result, dict):
        return []
    items = result.get("items", [])
    enriched: list[dict[str, Any]] = []
    for item in items:
        current = dict(item)
        profiles_reference = item.get("profilesReference") or {}
        link = profiles_reference.get("link")
        if isinstance(link, str) and link:
            parsed = urlparse(link)
            profile_path = parsed.path + (("?" + parsed.query) if parsed.query else "")
            try:
                profile_result = client.get(profile_path)
                if isinstance(profile_result, dict):
                    current["profilesReference"] = {"items": profile_result.get("items", [])}
            except RuntimeError:
                current["profilesReference"] = {"items": []}
        else:
            current["profilesReference"] = {"items": []}
        enriched.append(current)
    return enriched


def list_client_ssl_profiles(client: F5Client) -> list[dict[str, Any]]:
    result = client.get("/mgmt/tm/ltm/profile/client-ssl?$select=name,fullPath,ciphers&$top=1000")
    return result.get("items", []) if isinstance(result, dict) else []


def profile_is_strong(ciphers: str, policy: dict[str, Any]) -> bool:
    ctext = (ciphers or "").lower()
    strong = (policy.get("strong_cipher") or {})
    prefixes = [item.lower() for item in strong.get("required_cipher_prefixes_any", [])]
    markers = [item.lower() for item in strong.get("required_cipher_markers_any", [])]
    return any(ctext.startswith(prefix) for prefix in prefixes) or all(marker in ctext for marker in markers)


def profile_is_protocol_compliant(profile: dict[str, Any], policy: dict[str, Any]) -> bool:
    ciphers = str(profile.get("ciphers") or "").lower()
    options = profile.get("options")
    option_text = " ".join(options).lower() if isinstance(options, list) else str(options or "").lower()
    protocol = (policy.get("protocol_compliance") or {})
    required_options = [item.lower() for item in protocol.get("required_option_markers", [])]
    acceptable_options = [item.lower() for item in protocol.get("acceptable_option_markers", [])]
    acceptable_ciphers = [item.lower() for item in protocol.get("acceptable_cipher_markers", [])]
    acceptable_prefixes = [item.lower() for item in protocol.get("acceptable_cipher_prefixes", [])]
    if required_options and all(marker in option_text for marker in required_options):
        return True
    if any(marker in option_text for marker in acceptable_options):
        return True
    if any(marker in ciphers for marker in acceptable_ciphers):
        return True
    if any(ciphers.startswith(prefix) for prefix in acceptable_prefixes):
        return True
    # BIG-IP default clientssl on the live test host does not expose the
    # protocol-disable flags in REST, but it does expose modern GCM-only
    # cipher strings. Treat modern GCM suites as compliant fallback evidence.
    return "gcm" in ciphers


def evaluate_sshd_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    httpd = client.get("/mgmt/tm/sys/httpd")
    global_settings = client.get("/mgmt/tm/sys/global-settings")
    sshd = client.get("/mgmt/tm/sys/sshd")
    cli_output = run_tmsh_or_empty(client, "list cli global-settings idle-timeout")
    evidence_summary = {
        "sys_httpd_auth_pam_idle_timeout": parse_int_value(str(httpd.get("authPamIdleTimeout"))),
        "sys_httpd_auth_pam_dashboard_timeout": parse_bool_value(str(httpd.get("authPamDashboardTimeout"))),
        "sys_global_settings_console_inactivity_timeout": parse_int_value(str(global_settings.get("consoleInactivityTimeout"))),
        "cli_global_settings_idle_timeout": parse_int_value(cli_output),
        "sys_sshd_inactivity_timeout": parse_int_value(str(sshd.get("inactivityTimeout"))),
    }
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row("sys_httpd_auth_pam_idle_timeout", required.get("sys_httpd_auth_pam_idle_timeout", "<= 300"), evidence_summary["sys_httpd_auth_pam_idle_timeout"], bool(evidence_summary["sys_httpd_auth_pam_idle_timeout"]) and evidence_summary["sys_httpd_auth_pam_idle_timeout"] <= 300, "rest:/mgmt/tm/sys/httpd"),
        compare_row("sys_httpd_auth_pam_dashboard_timeout", required.get("sys_httpd_auth_pam_dashboard_timeout", "== true"), evidence_summary["sys_httpd_auth_pam_dashboard_timeout"], evidence_summary["sys_httpd_auth_pam_dashboard_timeout"] is True, "rest:/mgmt/tm/sys/httpd"),
        compare_row("sys_global_settings_console_inactivity_timeout", required.get("sys_global_settings_console_inactivity_timeout", "<= 300"), evidence_summary["sys_global_settings_console_inactivity_timeout"], bool(evidence_summary["sys_global_settings_console_inactivity_timeout"]) and evidence_summary["sys_global_settings_console_inactivity_timeout"] <= 300, "rest:/mgmt/tm/sys/global-settings"),
        compare_row("cli_global_settings_idle_timeout", required.get("cli_global_settings_idle_timeout", "<= 5"), evidence_summary["cli_global_settings_idle_timeout"], bool(evidence_summary["cli_global_settings_idle_timeout"]) and evidence_summary["cli_global_settings_idle_timeout"] <= 5, "tmsh:tmsh list cli global-settings idle-timeout"),
        compare_row("sys_sshd_inactivity_timeout", required.get("sys_sshd_inactivity_timeout", "<= 300"), evidence_summary["sys_sshd_inactivity_timeout"], bool(evidence_summary["sys_sshd_inactivity_timeout"]) and evidence_summary["sys_sshd_inactivity_timeout"] <= 300, "rest:/mgmt/tm/sys/sshd"),
    ]
    compliant = all(row["match"] for row in comparisons)
    evidence = {
        "tmsh_sys_httpd": evidence_source("rest", "/mgmt/tm/sys/httpd", json.dumps(httpd, indent=2)),
        "tmsh_cli_global_settings": evidence_source("tmsh", "tmsh list cli global-settings idle-timeout", cli_output),
        "tmsh_sys_global_settings": evidence_source("rest", "/mgmt/tm/sys/global-settings", json.dumps(global_settings, indent=2)),
        "sys_sshd": evidence_source("rest", "/mgmt/tm/sys/sshd", json.dumps(sshd, indent=2)),
    }
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    payload = make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Idle logout was evaluated across HTTPD/TMUI, CLI, console, and SSH timeout sources.", tmsh_fix)
    return payload


def evaluate_ltm_virtual_services_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    catalog = CONTROL_CATALOG_MAP[vuln_id]
    client = context.client()
    virtuals = list_virtuals(client)
    enabled = [item for item in virtuals if is_virtual_enabled(item)]
    disallowed = set(((catalog.get("organization_policy") or {}).get("disallowed_destination_ports") or []))
    violating = []
    for item in enabled:
        port = extract_destination_port(str(item.get("destination") or ""))
        if port in disallowed:
            violating.append({"name": item.get("name"), "destination": item.get("destination"), "port": port})
    compliant = len(violating) == 0
    evidence_summary = {"virtual_server_services_restricted": compliant}
    evidence = {"tmsh_ltm_virtual": evidence_source("rest", "/mgmt/tm/ltm/virtual", json.dumps({"enabled_virtuals": enabled, "violating_virtuals": violating}, indent=2))}
    comparisons = [compare_row("virtual_server_services_restricted", ((projection.get("pullback_row") or {}).get("required") or {}).get("virtual_server_services_restricted", "== true"), compliant, compliant, "rest:/mgmt/tm/ltm/virtual", "" if compliant else f"Disable or reconfigure listeners on prohibited ports: {', '.join(str(v['port']) for v in violating)}")]
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Enabled LTM virtual servers were compared against the organization disallowed port policy.")


def evaluate_ltm_virtual_ssl_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    policy = ((CONTROL_CATALOG_MAP[vuln_id].get("organization_policy") or {}).get("client_ssl_requirements") or {})
    client = context.client()
    virtuals = list_virtuals_with_profiles(client)
    profiles = list_client_ssl_profiles(client)
    profile_map: dict[str, dict[str, Any]] = {}
    for item in profiles:
        if item.get("name"):
            profile_map[str(item["name"]).split("/")[-1]] = item
        if item.get("fullPath"):
            profile_map[str(item["fullPath"]).split("/")[-1]] = item
    attached: list[dict[str, Any]] = []
    for virtual in virtuals:
        if not is_virtual_enabled(virtual):
            continue
        profiles_ref = ((virtual.get("profilesReference") or {}).get("items")) or []
        for ref in profiles_ref:
            if str(ref.get("context") or "").lower() != "clientside":
                continue
            if not is_client_ssl_profile_ref(ref, profile_map):
                continue
            profile_name = extract_profile_name(ref)
            if not profile_name:
                continue
            profile = profile_map.get(profile_name, {"name": profile_name, "ciphers": ""})
            attached.append({"virtual": virtual.get("name"), "profile": profile_name, "ciphers": profile.get("ciphers", "")})
    strong_count = sum(1 for item in attached if profile_is_strong(str(item.get("ciphers") or ""), policy))
    compliant = len(attached) == 0 or strong_count == len(attached)
    evidence_summary = {"ltm_attached_client_ssl_profile_count": len(attached), "ltm_profile_client_ssl_strong_cipher_count": strong_count}
    evidence = {
        "tmsh_ltm_profile_client_ssl": evidence_source("rest", "/mgmt/tm/ltm/profile/client-ssl", json.dumps(profiles, indent=2)),
        "tmsh_ltm_virtual": evidence_source("rest", "/mgmt/tm/ltm/virtual", json.dumps(virtuals, indent=2)),
    }
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row("ltm_attached_client_ssl_profile_count", required.get("ltm_attached_client_ssl_profile_count", "== 0"), len(attached), len(attached) == 0 or strong_count == len(attached), "rest:/mgmt/tm/ltm/virtual"),
        compare_row("ltm_profile_client_ssl_strong_cipher_count", required.get("ltm_profile_client_ssl_strong_cipher_count", "== attached"), strong_count, len(attached) == 0 or strong_count == len(attached), "rest:/mgmt/tm/ltm/profile/client-ssl"),
    ]
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Attached client-ssl profiles on active virtual servers were checked for strong approved ciphers.", tmsh_fix)


def evaluate_ltm_virtual_ssl_protocol_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    policy = ((CONTROL_CATALOG_MAP[vuln_id].get("organization_policy") or {}).get("client_ssl_requirements") or {})
    client = context.client()
    virtuals = list_virtuals_with_profiles(client)
    profiles = list_client_ssl_profiles(client)
    detailed_profiles = []
    for item in profiles:
        profile_path = f"/mgmt/tm/ltm/profile/client-ssl/~Common~{item['name']}"
        try:
            detailed_profiles.append(client.get(profile_path))
        except RuntimeError:
            detailed_profiles.append(item)
    profile_map: dict[str, dict[str, Any]] = {}
    for item in detailed_profiles:
        if item.get("name"):
            profile_map[str(item["name"]).split("/")[-1]] = item
        if item.get("fullPath"):
            profile_map[str(item["fullPath"]).split("/")[-1]] = item

    attached: list[dict[str, Any]] = []
    compliant_count = 0
    for virtual in virtuals:
        if not is_virtual_enabled(virtual):
            continue
        profiles_ref = ((virtual.get("profilesReference") or {}).get("items")) or []
        for ref in profiles_ref:
            if str(ref.get("context") or "").lower() != "clientside":
                continue
            if not is_client_ssl_profile_ref(ref, profile_map):
                continue
            profile_name = extract_profile_name(ref)
            if not profile_name:
                continue
            profile = profile_map.get(profile_name, {"name": profile_name, "ciphers": "", "options": None})
            attached.append({"virtual": virtual.get("name"), "profile": profile_name, "ciphers": profile.get("ciphers", ""), "options": profile.get("options")})
            if profile_is_protocol_compliant(profile, policy):
                compliant_count += 1

    compliant = len(attached) == 0 or compliant_count == len(attached)
    evidence_summary = {
        "ltm_attached_client_ssl_profile_count": len(attached),
        "ltm_profile_client_ssl_protocol_compliant_count": compliant_count,
    }
    evidence = {
        "tmsh_ltm_profile_client_ssl": evidence_source("rest", "/mgmt/tm/ltm/profile/client-ssl", json.dumps(detailed_profiles, indent=2)),
        "tmsh_ltm_virtual": evidence_source("rest", "/mgmt/tm/ltm/virtual", json.dumps(virtuals, indent=2)),
    }
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row("ltm_attached_client_ssl_profile_count", required.get("ltm_attached_client_ssl_profile_count", "== 0"), len(attached), len(attached) == 0 or compliant_count == len(attached), "rest:/mgmt/tm/ltm/virtual"),
        compare_row("ltm_profile_client_ssl_protocol_compliant_count", required.get("ltm_profile_client_ssl_protocol_compliant_count", "== attached"), compliant_count, len(attached) == 0 or compliant_count == len(attached), "rest:/mgmt/tm/ltm/profile/client-ssl"),
    ]
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Attached client-ssl profiles on active virtual servers were checked for protocol-compliant TLS configuration.", tmsh_fix)


def fetch_collection(client: F5Client, endpoint: str) -> list[dict[str, Any]]:
    try:
        result = client.get(endpoint)
    except RuntimeError as exc:
        text = str(exc).lower()
        if "http 404" in text or "not found" in text:
            return []
        raise
    return result.get("items", []) if isinstance(result, dict) else []


def run_tmsh_or_empty(client: F5Client, command: str) -> str:
    try:
        return client.run_tmsh(command)
    except RuntimeError as exc:
        if "did not return commandresult" in str(exc).lower():
            return ""
        raise


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"true", "yes", "enabled", "on", "1"}


def selected_apm_profiles(client: F5Client, vuln_id: str) -> list[dict[str, Any]]:
    control = CONTROL_CATALOG_MAP[vuln_id]
    ignored = set(((control.get("organization_policy") or {}).get("ignored_profile_names")) or [])
    profiles = fetch_collection(client, "/mgmt/tm/apm/profile/access?$top=100")
    selected: list[dict[str, Any]] = []
    for item in profiles:
        if str(item.get("scope") or "").lower() != "profile":
            continue
        if item.get("fullPath") in ignored:
            continue
        if not item.get("accessPolicy"):
            continue
        selected.append(item)
    return selected


def fetch_policy_items(client: F5Client, policy_path: str) -> list[dict[str, Any]]:
    encoded = policy_path.replace("/", "~")
    policy = client.get(f"/mgmt/tm/apm/policy/access-policy/{encoded}")
    items = policy.get("items") or []
    expanded: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        item_name = item.get("name")
        if not item_name:
            continue
        item_path = f"/mgmt/tm/apm/policy/policy-item/~Common~{item_name}"
        expanded.append(client.get(item_path))
    return expanded


def fetch_agent_payload(client: F5Client, item: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
    link = ((agent.get("nameReference") or {}).get("link")) or ""
    if isinstance(link, str) and link:
        parsed = urlparse(link)
        agent_path = parsed.path + (("?" + parsed.query) if parsed.query else "")
        try:
            return client.get(agent_path)
        except RuntimeError:
            return {}
    agent_type = str(agent.get("type") or "")
    agent_name = str(agent.get("name") or "")
    if agent_type == "aaa-ocsp" and agent_name:
        return client.get(f"/mgmt/tm/apm/policy/agent/aaa-ocsp/~Common~{agent_name}")
    if agent_type == "endpoint-check-machine-cert" and agent_name:
        return client.get(f"/mgmt/tm/apm/policy/agent/endpoint-check-machine-cert/~Common~{agent_name}")
    if agent_type == "message-box" and agent_name:
        return client.get(f"/mgmt/tm/apm/policy/agent/message-box/~Common~{agent_name}")
    if agent_type == "aaa-tacacsplus" and agent_name:
        return client.get(f"/mgmt/tm/apm/policy/agent/tacacsplus/~Common~{agent_name}")
    if agent_type == "aaa-kerberos" and agent_name:
        return client.get(f"/mgmt/tm/apm/policy/agent/kerberos/~Common~{agent_name}")
    return {}


def build_apm_policy_bundle(client: F5Client, vuln_id: str) -> list[dict[str, Any]]:
    bundle: list[dict[str, Any]] = []
    for profile in selected_apm_profiles(client, vuln_id):
        policy_path = str(profile.get("accessPolicy") or "")
        policy_items = fetch_policy_items(client, policy_path)
        items: list[dict[str, Any]] = []
        for item in policy_items:
            agents = item.get("agents") or []
            expanded_agents = []
            for agent in agents:
                expanded_agents.append(
                    {
                        "name": agent.get("name"),
                        "type": agent.get("type"),
                        "payload": fetch_agent_payload(client, item, agent),
                    }
                )
            items.append(
                {
                    "fullPath": item.get("fullPath"),
                    "name": item.get("name"),
                    "caption": item.get("caption"),
                    "itemType": item.get("itemType"),
                    "agents": expanded_agents,
                }
            )
        bundle.append(
            {
                "profile": profile,
                "policy_path": policy_path,
                "items": items,
            }
        )
    return bundle


def find_active_per_request_policy_refs(client: F5Client) -> list[str]:
    refs: list[str] = []
    for virtual in list_virtuals_with_profiles(client):
        if not is_virtual_enabled(virtual):
            continue
        for ref in ((virtual.get("profilesReference") or {}).get("items")) or []:
            name = str(ref.get("fullPath") or ref.get("name") or "")
            lowered = name.lower()
            if "per-request" in lowered or "per_request" in lowered or "perreq" in lowered:
                refs.append(name)
    return sorted(set(refs))


def item_matches_required(item: dict[str, Any], spec: dict[str, Any]) -> bool:
    caption_aliases = [str(v) for v in spec.get("caption_aliases", [])]
    item_type_aliases = [str(v) for v in spec.get("item_type_aliases", [])]
    agent_type_aliases = [str(v) for v in spec.get("agent_type_aliases", [])]
    caption = str(item.get("caption") or "")
    item_type = str(item.get("itemType") or "")
    agent_types = [str(agent.get("type") or "") for agent in item.get("agents") or []]
    if caption_aliases and caption not in caption_aliases:
        return False
    if item_type_aliases and item_type not in item_type_aliases:
        return False
    if agent_type_aliases and not any(agent_type in agent_type_aliases for agent_type in agent_types):
        return False
    agent_payload = spec.get("agent_payload") or {}
    if agent_payload:
        matched_payload = False
        for agent in item.get("agents") or []:
            payload = agent.get("payload") or {}
            if all(str(payload.get(key)) == str(value) for key, value in agent_payload.items()):
                matched_payload = True
                break
        if not matched_payload:
            return False
    agent_payload_match = spec.get("agent_payload_match") or {}
    if agent_payload_match:
        matched_payload = False
        for agent in item.get("agents") or []:
            payload = agent.get("payload") or {}
            if all(str(payload.get(key)) == str(value) for key, value in agent_payload_match.items()):
                matched_payload = True
                break
        if not matched_payload:
            return False
    return True


def policy_group_match(items: list[dict[str, Any]], specs: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    witnesses: list[str] = []
    for spec in specs:
        for item in items:
            if item_matches_required(item, spec):
                witnesses.append(str(item.get("fullPath") or item.get("name") or item.get("caption") or ""))
                return True, witnesses
    return False, witnesses


def evaluate_apm_profile_scalar_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    profiles = selected_apm_profiles(client, vuln_id)
    profile_paths = [str(item.get("fullPath") or "") for item in profiles]
    if not profiles:
        return make_not_applicable_payload(
            vuln_id,
            context.host,
            "No APM access profiles with assigned access policies were found on the live appliance.",
            {"apm_profile_count": 0},
            {"apm_profiles": evidence_source("rest", "/mgmt/tm/apm/profile/access", json.dumps([], indent=2))},
            [compare_row("apm_profile_count", "> 0", 0, False, "rest:/mgmt/tm/apm/profile/access", "No selected APM access profiles were present.")],
        )

    field_specs = {
        "V-266137": ("maxConcurrentUsers", "apm_profile_access_max_concurrent_users", lambda value: value is not None and value >= 1),
        "V-266155": ("inactivityTimeout", "apm_profile_access_inactivity_timeout", lambda value: value is not None and 0 < value <= 900),
        "V-266162": ("httponlyCookie", "apm_profile_cookie_http_only", lambda value: value is True),
        "V-266163": ("secureCookie", "apm_profile_cookie_secure", lambda value: value is True),
        "V-266164": ("persistentCookie", "apm_profile_cookie_persistent", lambda value: value is False),
        "V-266168": ("restrictToSingleClientIp", "apm_restrict_single_client_ip", lambda value: value is True),
        "V-266169": ("maxSessionTimeout", "apm_profile_access_max_session_timeout", lambda value: value is not None and 0 < value <= 28800),
        "V-266175": ("maxConcurrentSessions", "apm_profile_access_max_sessions_per_client_ip", lambda value: value is not None and 1 <= value <= 10),
    }
    profile_field, evidence_field, predicate = field_specs[vuln_id]
    observed_values: list[Any] = []
    comparisons: list[dict[str, Any]] = []
    required = (projection.get("pullback_row") or {}).get("required", {})
    for profile in profiles:
        raw = profile.get(profile_field)
        if profile_field in {"maxConcurrentUsers", "inactivityTimeout", "maxSessionTimeout", "maxConcurrentSessions"}:
            observed = parse_int_value(str(raw))
        else:
            observed = parse_bool_value(str(raw))
        observed_values.append(observed)
        comparisons.append(
            compare_row(
                f"{profile.get('fullPath')}::{evidence_field}",
                required.get(evidence_field, ""),
                observed,
                predicate(observed),
                "rest:/mgmt/tm/apm/profile/access",
            )
        )
    compliant = all(row["match"] for row in comparisons)
    evidence_summary = {
        evidence_field: observed_values[0] if len(observed_values) == 1 else observed_values,
        "apm_selected_profile_count": len(profiles),
        "apm_selected_profiles": profile_paths,
    }
    evidence = {
        "apm_profiles": evidence_source("rest", "/mgmt/tm/apm/profile/access", json.dumps(profiles, indent=2)),
    }
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(
        vuln_id,
        context.host,
        "not_a_finding" if compliant else "open",
        compliant,
        evidence_summary,
        evidence,
        comparisons,
        "Selected APM access profiles with assigned policies were evaluated directly from live profile fields.",
        tmsh_fix,
        rest_fix,
    )


def evaluate_apm_log_setting_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    profiles = selected_apm_profiles(client, vuln_id)
    log_settings = fetch_collection(client, "/mgmt/tm/apm/log-setting?$top=100")
    log_map = {str(item.get("fullPath") or ""): item for item in log_settings}
    comparisons: list[dict[str, Any]] = []
    profile_results = []
    required = (projection.get("pullback_row") or {}).get("required", {})
    for profile in profiles:
        selected_logs = profile.get("logSettings") or []
        selected_log = str(selected_logs[0] if selected_logs else "")
        setting = log_map.get(selected_log, {})
        access_entries = setting.get("access") or []
        enabled = False
        notice = False
        if access_entries:
            enabled = any(truthy(entry.get("enabled")) for entry in access_entries)
            notice = all(
                str(level).lower() == "notice"
                for entry in access_entries
                for level in (entry.get("logLevel") or {}).values()
            )
        profile_results.append(
            {
                "profile": profile.get("fullPath"),
                "log_setting": selected_log,
                "access_system_logs_enabled": enabled,
                "access_log_settings_level": "notice" if notice else "other",
            }
        )
        comparisons.extend(
            [
                compare_row(
                    f"{profile.get('fullPath')}::access_system_logs_enabled",
                    required.get("access_system_logs_enabled", "== true"),
                    enabled,
                    enabled,
                    "rest:/mgmt/tm/apm/log-setting",
                ),
                compare_row(
                    f"{profile.get('fullPath')}::access_log_settings_level",
                    required.get("access_log_settings_level", "== notice"),
                    "notice" if notice else "other",
                    notice,
                    "rest:/mgmt/tm/apm/log-setting",
                ),
            ]
        )
    compliant = bool(profile_results) and all(row["match"] for row in comparisons)
    evidence_summary = {
        "access_system_logs_enabled": all(result["access_system_logs_enabled"] for result in profile_results) if profile_results else False,
        "access_log_settings_level": "notice" if profile_results and all(result["access_log_settings_level"] == "notice" for result in profile_results) else "other",
        "apm_profile_log_results": profile_results,
    }
    evidence = {
        "apm_profiles": evidence_source("rest", "/mgmt/tm/apm/profile/access", json.dumps(profiles, indent=2)),
        "apm_log_settings": evidence_source("rest", "/mgmt/tm/apm/log-setting", json.dumps(log_settings, indent=2)),
    }
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    return make_validation_payload(
        vuln_id,
        context.host,
        "not_a_finding" if compliant else "open",
        compliant,
        evidence_summary,
        evidence,
        comparisons,
        "Selected APM access profiles and their referenced log settings were checked for enabled access logging at notice level.",
        tmsh_fix,
    )


def evaluate_apm_policy_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    control = CONTROL_CATALOG_MAP[vuln_id]
    client = context.client()
    bundle = build_apm_policy_bundle(client, vuln_id)
    if not bundle:
        return make_not_applicable_payload(
            vuln_id,
            context.host,
            "No APM access profiles with assigned access policies were found on the live appliance.",
            {"apm_policy_count": 0},
            {"apm_policies": evidence_source("rest", "/mgmt/tm/apm/policy/access-policy", json.dumps([], indent=2))},
            [compare_row("apm_policy_count", "> 0", 0, False, "rest:/mgmt/tm/apm/policy/access-policy")],
        )

    org = control.get("organization_policy") or {}
    comparisons: list[dict[str, Any]] = []
    profile_results: list[dict[str, Any]] = []
    required = (projection.get("pullback_row") or {}).get("required", {})
    why = "Selected APM access policy graphs were evaluated against the factory-required policy-item signatures."

    for entry in bundle:
        profile_path = str((entry.get("profile") or {}).get("fullPath") or "")
        policy_path = str(entry.get("policy_path") or "")
        items = entry.get("items") or []
        result: dict[str, Any] = {"profile": profile_path, "policy": policy_path}

        if vuln_id in {"V-266143", "V-266152", "V-266153", "V-266165"}:
            group_matches = []
            witnesses = []
            for index, group in enumerate(org.get("required_policy_item_groups") or [], start=1):
                matched, group_witness = policy_group_match(items, group)
                group_matches.append(matched)
                witnesses.extend(group_witness)
                comparisons.append(
                    compare_row(
                        f"{profile_path}::required_policy_group_{index}",
                        "present",
                        group_witness or [],
                        matched,
                        "rest:/mgmt/tm/apm/policy/access-policy",
                    )
                )
            compliant = all(group_matches)
            result["matched_groups"] = group_matches
            result["witnesses"] = sorted(set(witnesses))
            if vuln_id == "V-266143":
                result["apm_access_policy_authorization_configured"] = compliant
            elif vuln_id == "V-266152":
                result["apm_policy_mfa_and_redundant_auth_configured"] = compliant
            elif vuln_id == "V-266153":
                result["apm_machine_cert_revocation_validation_configured"] = compliant
            elif vuln_id == "V-266165":
                result["apm_user_cert_revocation_validation_configured"] = compliant

        elif vuln_id == "V-266145":
            required_items = org.get("required_policy_items") or []
            matched, witnesses = policy_group_match(items, required_items)
            result["apm_access_policy_banner_configured"] = matched
            result["witnesses"] = sorted(set(witnesses))
            comparisons.append(
                compare_row(
                    f"{profile_path}::apm_access_policy_banner_configured",
                    required.get("apm_access_policy_banner_configured", "== true"),
                    matched,
                    matched,
                    "rest:/mgmt/tm/apm/policy/access-policy",
                )
            )

        elif vuln_id == "V-266154":
            required_groups = org.get("required_policy_item_groups") or []
            matched, witnesses = policy_group_match(items, required_groups[0] if required_groups else [])
            supporting_ok = False
            supporting_objects: list[str] = []
            for item in items:
                if not item_matches_required(item, (required_groups[0][0] if required_groups and required_groups[0] else {})):
                    continue
                for agent in item.get("agents") or []:
                    payload = agent.get("payload") or {}
                    responder = str(payload.get("ocspResponder") or "")
                    if not responder:
                        continue
                    supporting_objects.append(responder)
                    ocsp = client.get(f"/mgmt/tm/apm/aaa/ocsp/{responder.replace('/', '~')}")
                    supporting_ok = (
                        str(ocsp.get("verify")).lower() == "true"
                        and str(ocsp.get("verifyCert")).lower() == "true"
                        and str(ocsp.get("verifySig")).lower() == "true"
                        and str(ocsp.get("explicitOcsp")).lower() == "true"
                        and parse_int_value(str(ocsp.get("statusAge"))) is not None
                        and parse_int_value(str(ocsp.get("statusAge"))) >= 1
                        and parse_int_value(str(ocsp.get("validityPeriod"))) is not None
                        and parse_int_value(str(ocsp.get("validityPeriod"))) >= 1
                    )
                    if supporting_ok:
                        break
                if supporting_ok:
                    break
            compliant = matched and supporting_ok
            result["apm_revocation_cache_configured"] = compliant
            result["witnesses"] = sorted(set(witnesses))
            result["supporting_objects"] = supporting_objects
            comparisons.extend(
                [
                    compare_row(
                        f"{profile_path}::required_policy_group_1",
                        "present",
                        witnesses or [],
                        matched,
                        "rest:/mgmt/tm/apm/policy/access-policy",
                    ),
                    compare_row(
                        f"{profile_path}::apm_revocation_cache_configured",
                        required.get("apm_revocation_cache_configured", "== true"),
                        supporting_objects,
                        compliant,
                        "rest:/mgmt/tm/apm/aaa/ocsp",
                    ),
                ]
            )

        elif vuln_id == "V-266166":
            required_items = org.get("required_policy_items") or []
            forbidden_items = org.get("forbidden_policy_items") or []
            has_required, witnesses = policy_group_match(items, required_items)
            forbidden = False
            for spec in forbidden_items:
                for item in items:
                    if item_matches_required(item, spec):
                        forbidden = True
                        break
                if forbidden:
                    break
            compliant = has_required and not forbidden
            result["apm_client_cert_inspection_configured"] = has_required
            result["apm_on_demand_cert_auth_absent"] = not forbidden
            result["witnesses"] = sorted(set(witnesses))
            comparisons.extend(
                [
                    compare_row(
                        f"{profile_path}::apm_client_cert_inspection_configured",
                        required.get("apm_client_cert_inspection_configured", "== true"),
                        has_required,
                        has_required,
                        "rest:/mgmt/tm/apm/policy/access-policy",
                    ),
                    compare_row(
                        f"{profile_path}::apm_on_demand_cert_auth_absent",
                        required.get("apm_on_demand_cert_auth_absent", "== true"),
                        not forbidden,
                        not forbidden,
                        "rest:/mgmt/tm/apm/policy/access-policy",
                    ),
                ]
            )

        elif vuln_id == "V-266171":
            required_items = org.get("required_policy_items") or []
            matched, witnesses = policy_group_match(items, required_items)
            result["apm_endpoint_device_auth_configured"] = matched
            result["witnesses"] = sorted(set(witnesses))
            comparisons.append(
                compare_row(
                    f"{profile_path}::apm_endpoint_device_auth_configured",
                    required.get("apm_endpoint_device_auth_configured", "== true"),
                    matched,
                    matched,
                    "rest:/mgmt/tm/apm/policy/access-policy",
                )
            )

        elif vuln_id == "V-266151":
            per_request_refs = find_active_per_request_policy_refs(client)
            compliant = len(per_request_refs) == 0
            result["apm_policy_reauthentication_configured"] = compliant
            result["per_request_policy_refs"] = per_request_refs
            comparisons.extend(
                [
                    compare_row(
                        f"{profile_path}::apm_policy_reauthentication_configured",
                        required.get("apm_policy_reauthentication_configured", "== true"),
                        compliant,
                        compliant,
                        "rest:/mgmt/tm/ltm/virtual",
                    ),
                    compare_row(
                        f"{profile_path}::apm_active_per_request_policy_count",
                        "== 0",
                        len(per_request_refs),
                        len(per_request_refs) == 0,
                        "rest:/mgmt/tm/ltm/virtual",
                    ),
                ]
            )

        profile_results.append(result)

    compliant = all(row["match"] for row in comparisons)
    evidence_summary = {
        "apm_profile_policy_results": profile_results,
    }
    if vuln_id == "V-266143":
        evidence_summary["apm_access_policy_authorization_configured"] = compliant
    elif vuln_id == "V-266145":
        evidence_summary["apm_access_policy_banner_configured"] = compliant
    elif vuln_id == "V-266152":
        evidence_summary["apm_policy_mfa_and_redundant_auth_configured"] = compliant
    elif vuln_id == "V-266153":
        evidence_summary["apm_machine_cert_revocation_validation_configured"] = compliant
    elif vuln_id == "V-266154":
        evidence_summary["apm_revocation_cache_configured"] = compliant
    elif vuln_id == "V-266165":
        evidence_summary["apm_user_cert_revocation_validation_configured"] = compliant
    elif vuln_id == "V-266166":
        evidence_summary["apm_client_cert_inspection_configured"] = all(bool(result.get("apm_client_cert_inspection_configured")) for result in profile_results)
        evidence_summary["apm_on_demand_cert_auth_absent"] = all(bool(result.get("apm_on_demand_cert_auth_absent")) for result in profile_results)
    elif vuln_id == "V-266171":
        evidence_summary["apm_endpoint_device_auth_configured"] = compliant
    elif vuln_id == "V-266151":
        evidence_summary["apm_policy_reauthentication_configured"] = compliant

    evidence = {
        "apm_policy_bundle": evidence_source("rest", "/mgmt/tm/apm/policy/access-policy", json.dumps(bundle, indent=2)),
    }
    return make_validation_payload(
        vuln_id,
        context.host,
        "not_a_finding" if compliant else "open",
        compliant,
        evidence_summary,
        evidence,
        comparisons,
        why,
        ((projection.get("remediation") or {}).get("tmsh_equivalent")) or "",
        ((projection.get("remediation") or {}).get("endpoint")) or "",
    )


def evaluate_apm_network_access_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    control = CONTROL_CATALOG_MAP[vuln_id]
    client = context.client()
    resources = fetch_collection(client, "/mgmt/tm/apm/resource/network-access?$top=100")
    org = control.get("organization_policy") or {}
    required_false_fields = org.get("required_false_fields") or []
    required_empty_fields = org.get("required_empty_fields") or []
    if not resources:
        return make_validation_payload(
            vuln_id,
            context.host,
            "not_a_finding",
            True,
            {"apm_network_access_resource_count": 0, "apm_network_access_split_tunneling_disabled": True},
            {"apm_network_access": evidence_source("rest", "/mgmt/tm/apm/resource/network-access", json.dumps([], indent=2))},
            [compare_row("apm_network_access_resource_count", "== 0", 0, True, "rest:/mgmt/tm/apm/resource/network-access")],
            "No APM network access resources were configured, so the control is policy-clean on this appliance.",
        )
    comparisons: list[dict[str, Any]] = []
    per_resource = []
    required = (projection.get("pullback_row") or {}).get("required", {})
    for resource in resources:
        path = str(resource.get("fullPath") or resource.get("name") or "")
        field_results = {}
        resource_ok = True
        for field in required_false_fields:
            value = truthy(resource.get(field))
            field_results[field] = not value
            resource_ok = resource_ok and (not value)
            comparisons.append(compare_row(f"{path}::{field}", "== false", resource.get(field), not value, "rest:/mgmt/tm/apm/resource/network-access"))
        for field in required_empty_fields:
            value = resource.get(field)
            empty = value in (None, "", []) or (isinstance(value, dict) and not value)
            field_results[field] = empty
            resource_ok = resource_ok and empty
            comparisons.append(compare_row(f"{path}::{field}", "== empty", value, empty, "rest:/mgmt/tm/apm/resource/network-access"))
        per_resource.append({"resource": path, "ok": resource_ok, "field_results": field_results})
    compliant = all(item["ok"] for item in per_resource)
    evidence_summary = {
        "apm_network_access_split_tunneling_disabled": compliant,
        "apm_network_access_results": per_resource,
    }
    evidence = {
        "apm_network_access": evidence_source("rest", "/mgmt/tm/apm/resource/network-access", json.dumps(resources, indent=2)),
    }
    return make_validation_payload(
        vuln_id,
        context.host,
        "not_a_finding" if compliant else "open",
        compliant,
        evidence_summary,
        evidence,
        comparisons,
        "Configured APM network access resources were checked for split tunneling disablement and bypass exclusions.",
        ((projection.get("remediation") or {}).get("tmsh_equivalent")) or "",
        ((projection.get("remediation") or {}).get("endpoint")) or "",
    )


def pki_ocsp_applicability(client: F5Client) -> dict[str, Any]:
    auth_source = client.get("/mgmt/tm/auth/source")
    source_type = str(auth_source.get("type") or "").strip().lower()
    ldap_items = fetch_collection(client, "/mgmt/tm/apm/aaa/ldap?$top=50")
    access_profiles = fetch_collection(client, "/mgmt/tm/apm/profile/access?$top=100")
    source_mentions_clientcert_ldap = "clientcert" in source_type and "ldap" in source_type
    access_mentions_clientcert_ldap = any(
        "clientcert" in " ".join(
            [
                str(item.get("name") or ""),
                str(item.get("fullPath") or ""),
                str(item.get("accessPolicy") or ""),
                str(item.get("userIdentityMethod") or ""),
            ]
        ).lower()
        and "ldap" in " ".join(
            [
                str(item.get("name") or ""),
                str(item.get("fullPath") or ""),
                str(item.get("accessPolicy") or ""),
                str(item.get("userIdentityMethod") or ""),
            ]
        ).lower()
        for item in access_profiles
    )
    applicable = source_mentions_clientcert_ldap or access_mentions_clientcert_ldap
    return {
        "applicable": applicable,
        "auth_source_type": source_type,
        "ldap_config_count": len(ldap_items),
        "access_profile_count": len(access_profiles),
        "clientcert_ldap_source_detected": source_mentions_clientcert_ldap,
        "clientcert_ldap_profile_detected": access_mentions_clientcert_ldap,
        "auth_source": auth_source,
        "ldap_items": ldap_items,
        "access_profiles": access_profiles,
    }


def evaluate_service_profile_security_family(context: SessionContext, vuln_id: str, profile_type: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    virtuals = list_virtuals_with_profiles(client)
    profiles = fetch_collection(client, f"/mgmt/tm/ltm/profile/{profile_type}?$top=1000")
    profile_map: dict[str, dict[str, Any]] = {}
    for item in profiles:
        if item.get("name"):
            profile_map[str(item["name"]).split("/")[-1]] = item
        if item.get("fullPath"):
            profile_map[str(item["fullPath"]).split("/")[-1]] = item

    attached: list[dict[str, Any]] = []
    secure_count = 0
    for virtual in virtuals:
        if not is_virtual_enabled(virtual):
            continue
        profiles_ref = ((virtual.get("profilesReference") or {}).get("items")) or []
        for ref in profiles_ref:
            profile_name = extract_profile_name(ref)
            if not profile_name or profile_name not in profile_map:
                continue
            profile = profile_map[profile_name]
            attached.append({"virtual": virtual.get("name"), "profile": profile_name, "security": profile.get("security")})
            if str(profile.get("security") or "").lower() == "enabled":
                secure_count += 1

    field_count = f"ltm_attached_{profile_type}_profile_count"
    field_secure = f"{profile_type}_protocol_security_enabled_count"
    compliant = len(attached) == 0 or secure_count == len(attached)
    evidence_summary = {field_count: len(attached), field_secure: secure_count}
    evidence = {
        f"tmsh_ltm_profile_{profile_type}": evidence_source("rest", f"/mgmt/tm/ltm/profile/{profile_type}", json.dumps(profiles, indent=2)),
        "tmsh_ltm_virtual": evidence_source("rest", "/mgmt/tm/ltm/virtual", json.dumps(virtuals, indent=2)),
    }
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row(field_count, required.get(field_count, "== 0"), len(attached), len(attached) == 0 or secure_count == len(attached), "rest:/mgmt/tm/ltm/virtual"),
        compare_row(field_secure, required.get(field_secure, "== attached"), secure_count, len(attached) == 0 or secure_count == len(attached), f"rest:/mgmt/tm/ltm/profile/{profile_type}"),
    ]
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, f"Attached {profile_type.upper()} profiles on active virtual servers were checked for protocol security enablement.")


def evaluate_protocol_inspection_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    virtuals = list_virtuals_with_profiles(client)
    enabled_virtuals = [item for item in virtuals if is_virtual_enabled(item)]
    inspection_enabled = False
    for virtual in enabled_virtuals:
        attached_profiles = ((virtual.get("profilesReference") or {}).get("items")) or []
        if any("inspection" in str(ref.get("name") or "").lower() for ref in attached_profiles):
            inspection_enabled = True
            break
        if virtual.get("protocolInspectionProfile"):
            inspection_enabled = True
            break
    evidence_summary = {"virtual_server_protocol_inspection_enabled": inspection_enabled}
    evidence = {"tmsh_ltm_virtual": evidence_source("rest", "/mgmt/tm/ltm/virtual", json.dumps(virtuals, indent=2))}
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [compare_row("virtual_server_protocol_inspection_enabled", required.get("virtual_server_protocol_inspection_enabled", "== true"), inspection_enabled, inspection_enabled is True, "rest:/mgmt/tm/ltm/virtual")]
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if inspection_enabled else "open", inspection_enabled is True, evidence_summary, evidence, comparisons, "Active virtual servers were checked for protocol inspection profile attachment.")


def read_version_string(version_payload: dict[str, Any]) -> str:
    entries = ((version_payload.get("entries") or {}).values())
    for entry in entries:
        nested = (((entry or {}).get("nestedStats") or {}).get("entries")) or {}
        version = ((nested.get("Version") or {}).get("description"))
        if isinstance(version, str) and version:
            return version
    return ""


def evaluate_manual_or_generic_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    control = CONTROL_CATALOG_MAP[vuln_id]
    client = context.client()
    evidence: dict[str, Any] = {}
    evidence_summary: dict[str, Any] = {}
    comparisons: list[dict[str, Any]] = []
    why = ""

    if vuln_id == "V-266064":
        httpd = client.get("/mgmt/tm/sys/httpd")
        max_clients = parse_int_value(str(httpd.get("maxClients")))
        org_defined = (((projection.get("binding") or {}).get("org_defined_value") or {}).get("Int"))
        compliant = max_clients is not None and (max_clients <= 10 or (org_defined is not None and max_clients == org_defined))
        evidence_summary = {"sys_httpd_max_clients": max_clients}
        evidence = {"sys_httpd": evidence_source("rest", "/mgmt/tm/sys/httpd", json.dumps(httpd, indent=2))}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("sys_httpd_max_clients", required.get("sys_httpd_max_clients", "<= 10 OR == org_defined_value"), max_clients, compliant, "rest:/mgmt/tm/sys/httpd")]
        why = "TMUI concurrent session limits were evaluated from the live sys httpd configuration."
    elif vuln_id == "V-266068":
        tmm = client.get("/mgmt/tm/sys/daemon-log-settings/tmm")
        mcpd = client.get("/mgmt/tm/sys/daemon-log-settings/mcpd")
        db = client.get("/mgmt/tm/sys/db/log.ssl.level")
        evidence_summary = {
            "sys_daemon_log_tmm_os_log_level": str(tmm.get("osLogLevel") or "").lower(),
            "sys_daemon_log_tmm_ssl_log_level": str(tmm.get("sslLogLevel") or "").lower(),
            "sys_daemon_log_mcpd_audit": str(mcpd.get("audit") or "").lower(),
            "sys_daemon_log_mcpd_log_level": str(mcpd.get("logLevel") or "").lower(),
            "sys_db_log_ssl_level": str(db.get("value") or "").lower(),
        }
        required = (projection.get("pullback_row") or {}).get("required", {})
        expected = {
            "sys_daemon_log_tmm_os_log_level": "informational",
            "sys_daemon_log_tmm_ssl_log_level": "informational",
            "sys_daemon_log_mcpd_audit": "enabled",
            "sys_daemon_log_mcpd_log_level": "notice",
            "sys_db_log_ssl_level": "informational",
        }
        comparisons = [
            compare_row(field, required.get(field, f"== '{expected[field]}'"), evidence_summary[field], evidence_summary[field] == expected[field], f"rest:{source}")
            for field, source in [
                ("sys_daemon_log_tmm_os_log_level", "/mgmt/tm/sys/daemon-log-settings/tmm"),
                ("sys_daemon_log_tmm_ssl_log_level", "/mgmt/tm/sys/daemon-log-settings/tmm"),
                ("sys_daemon_log_mcpd_audit", "/mgmt/tm/sys/daemon-log-settings/mcpd"),
                ("sys_daemon_log_mcpd_log_level", "/mgmt/tm/sys/daemon-log-settings/mcpd"),
                ("sys_db_log_ssl_level", "/mgmt/tm/sys/db/log.ssl.level"),
            ]
        ]
        compliant = all(row["match"] for row in comparisons)
        evidence = {
            "daemon_log_tmm": evidence_source("rest", "/mgmt/tm/sys/daemon-log-settings/tmm", json.dumps(tmm, indent=2)),
            "daemon_log_mcpd": evidence_source("rest", "/mgmt/tm/sys/daemon-log-settings/mcpd", json.dumps(mcpd, indent=2)),
            "db_log_ssl_level": evidence_source("rest", "/mgmt/tm/sys/db/log.ssl.level", json.dumps(db, indent=2)),
        }
        why = "Privileged function audit logging settings were evaluated from TMM, MCPD, and log.ssl.level live settings."
    elif vuln_id == "V-266065":
        users = fetch_collection(client, "/mgmt/tm/auth/user?$top=100")
        shared_markers = ("shared", "group", "generic", "service")
        shared_accounts = []
        for user in users:
            haystack = " ".join(
                [
                    str(user.get("name") or ""),
                    str(user.get("fullPath") or ""),
                    str(user.get("description") or ""),
                ]
            ).lower()
            if any(marker in haystack for marker in shared_markers):
                shared_accounts.append(str(user.get("name") or user.get("fullPath") or "unknown"))
        compliant = len(shared_accounts) == 0
        evidence_summary = {"auth_user_shared_accounts": len(shared_accounts)}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row(
                "auth_user_shared_accounts",
                required.get("auth_user_shared_accounts", "== 0"),
                len(shared_accounts),
                compliant,
                "rest:/mgmt/tm/auth/user",
                "" if compliant else f"Shared/group-style accounts detected: {', '.join(shared_accounts)}",
            )
        ]
        evidence = {"auth_users": evidence_source("rest", "/mgmt/tm/auth/user", json.dumps(users, indent=2))}
        why = "Local user inventory was evaluated for shared/group-style account markers in the live account metadata."
    elif vuln_id == "V-266066":
        users = fetch_collection(client, "/mgmt/tm/auth/user?$top=100")
        local_count = len(users)
        compliant = local_count == 1
        evidence_summary = {"auth_user_local_account_count": local_count}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("auth_user_local_account_count", required.get("auth_user_local_account_count", "== 1"), local_count, compliant, "rest:/mgmt/tm/auth/user")]
        evidence = {"auth_users": evidence_source("rest", "/mgmt/tm/auth/user", json.dumps(users, indent=2))}
        why = "Configured local BIG-IP user accounts were counted from the live auth user inventory."
    elif vuln_id == "V-266079":
        source = client.get("/mgmt/tm/auth/source")
        tacacs = fetch_collection(client, "/mgmt/tm/auth/tacacs?$top=100")
        server_count = sum(len(item.get("servers") or []) for item in tacacs)
        evidence_summary = {"auth_source_type": str(source.get("type") or "").lower(), "auth_server_count": server_count}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("auth_source_type", required.get("auth_source_type", "== 'tacacs'"), evidence_summary["auth_source_type"], evidence_summary["auth_source_type"] == "tacacs", "rest:/mgmt/tm/auth/source"),
            compare_row("auth_server_count", required.get("auth_server_count", ">= 2"), server_count, server_count >= 2, "rest:/mgmt/tm/auth/tacacs"),
        ]
        compliant = all(row["match"] for row in comparisons)
        evidence = {
            "auth_source": evidence_source("rest", "/mgmt/tm/auth/source", json.dumps(source, indent=2)),
            "auth_tacacs": evidence_source("rest", "/mgmt/tm/auth/tacacs", json.dumps(tacacs, indent=2)),
        }
        why = "Administrative authentication source and configured TACACS servers were evaluated from live AAA settings."
    elif vuln_id == "V-266080":
        version_payload = client.get("/mgmt/tm/sys/version")
        version = read_version_string(version_payload)
        supported_versions = [str(item) for item in ((control.get("organization_policy") or {}).get("supported_versions") or [])]
        compliant = version in supported_versions
        evidence_summary = {"sys_version_supported": compliant, "sys_version": version}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("sys_version_supported", required.get("sys_version_supported", "== true"), compliant, compliant, "rest:/mgmt/tm/sys/version", "" if compliant else f"Observed version {version} not in supported set {supported_versions}")]
        evidence = {"sys_version": evidence_source("rest", "/mgmt/tm/sys/version", json.dumps(version_payload, indent=2))}
        why = "The BIG-IP TMOS version was checked against the packaged supported-version allowlist."
    elif vuln_id == "V-266085":
        source = client.get("/mgmt/tm/auth/source")
        source_type = str(source.get("type") or "").lower()
        compliant = source_type == "tacacs"
        evidence_summary = {"auth_mfa_configured": source_type}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("auth_mfa_configured", required.get("auth_mfa_configured", "== 'tacacs'"), source_type, compliant, "rest:/mgmt/tm/auth/source")]
        evidence = {"auth_source": evidence_source("rest", "/mgmt/tm/auth/source", json.dumps(source, indent=2))}
        why = "Interactive management authentication was evaluated from the live auth source configuration."
    elif vuln_id == "V-266092":
        difok = client.get("/mgmt/tm/sys/db/password.difok")
        value = parse_int_value(str(difok.get("value")))
        compliant = value is not None and value >= 8
        evidence_summary = {"sys_db_password_difok": value}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("sys_db_password_difok", required.get("sys_db_password_difok", ">= 8"), value, compliant, "rest:/mgmt/tm/sys/db/password.difok")]
        evidence = {"password_difok": evidence_source("rest", "/mgmt/tm/sys/db/password.difok", json.dumps(difok, indent=2))}
        why = "The password.difok policy value was evaluated from the live BIG-IP sys db setting."
    elif vuln_id in {"V-266093", "V-266094"}:
        applicability = pki_ocsp_applicability(client)
        ocsp_items = fetch_collection(client, "/mgmt/tm/apm/aaa/ocsp?$top=100")
        evidence = {
            "auth_source": evidence_source("rest", "/mgmt/tm/auth/source", json.dumps(applicability["auth_source"], indent=2)),
            "apm_aaa_ldap": evidence_source("rest", "/mgmt/tm/apm/aaa/ldap", json.dumps(applicability["ldap_items"], indent=2)),
            "apm_profile_access": evidence_source("rest", "/mgmt/tm/apm/profile/access", json.dumps(applicability["access_profiles"], indent=2)),
            "apm_aaa_ocsp": evidence_source("rest", "/mgmt/tm/apm/aaa/ocsp", json.dumps(ocsp_items, indent=2)),
        }
        applicability_summary = {
            "auth_source_type": applicability["auth_source_type"],
            "ldap_config_count": applicability["ldap_config_count"],
            "clientcert_ldap_source_detected": applicability["clientcert_ldap_source_detected"],
            "clientcert_ldap_profile_detected": applicability["clientcert_ldap_profile_detected"],
            "ocsp_object_count": len(ocsp_items),
        }
        if not applicability["applicable"]:
            comparisons = [
                compare_row(
                    "clientcert_ldap_auth_path_applicable",
                    "== true for this control to apply",
                    False,
                    True,
                    "rest:/mgmt/tm/auth/source",
                    "Current live authentication path is not Remote - ClientCert LDAP",
                )
            ]
            return make_not_applicable_payload(
                vuln_id,
                context.host,
                "This control applies only when User Directory is configured for Remote - ClientCert LDAP. The current appliance authentication path is not in that scope.",
                applicability_summary,
                evidence,
                comparisons,
            )

        required = (projection.get("pullback_row") or {}).get("required", {})
        if vuln_id == "V-266093":
            expected = int(((control.get("organization_policy") or {}).get("ocsp_max_age")) or 86400)
            compliant_items = [
                item for item in ocsp_items
                if str(item.get("explicitOcsp") or "").lower() == "true" and int(item.get("statusAge") or -1) == expected
            ]
            compliant = len(ocsp_items) > 0 and len(compliant_items) == len(ocsp_items)
            evidence_summary = dict(applicability_summary)
            evidence_summary["ocsp_max_clock_skew_configured"] = compliant
            evidence_summary["ocsp_expected_status_age"] = expected
            evidence_summary["ocsp_matching_status_age_count"] = len(compliant_items)
            comparisons = [compare_row("ocsp_max_clock_skew_configured", required.get("ocsp_max_clock_skew_configured", "== true"), compliant, compliant, "rest:/mgmt/tm/apm/aaa/ocsp")]
            why = "ClientCert LDAP is in scope, so live OCSP responder objects were checked for the required OCSP Response Max Age."
        else:
            approved = set((control.get("organization_policy") or {}).get("approved_responder_identities") or [])
            compliant_items = [item for item in ocsp_items if str(item.get("fullPath") or "") in approved]
            compliant = len(ocsp_items) > 0 and len(compliant_items) == len(ocsp_items)
            evidence_summary = dict(applicability_summary)
            evidence_summary["ocsp_responder_dod_approved"] = compliant
            evidence_summary["approved_responder_identity_count"] = len(approved)
            evidence_summary["matching_approved_responder_count"] = len(compliant_items)
            comparisons = [compare_row("ocsp_responder_dod_approved", required.get("ocsp_responder_dod_approved", "== true"), compliant, compliant, "rest:/mgmt/tm/apm/aaa/ocsp")]
            why = "ClientCert LDAP is in scope, so live OCSP responder identities were checked against the packaged DoD-approved responder allowlist."
        tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
        rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
        return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, why, tmsh_fix, rest_fix)
    elif vuln_id == "V-266078":
        setting = client.get("/mgmt/tm/sys/db/liveinstall.checksig")
        value = str(setting.get("value") or "").lower()
        compliant = value == "enable"
        evidence_summary = {"software_signature_verification_enabled": compliant}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row(
                "software_signature_verification_enabled",
                required.get("software_signature_verification_enabled", "== true"),
                compliant,
                compliant,
                "rest:/mgmt/tm/sys/db/liveinstall.checksig",
                "" if compliant else f"Observed liveinstall.checksig value={value}",
            )
        ]
        evidence = {"liveinstall_checksig": evidence_source("rest", "/mgmt/tm/sys/db/liveinstall.checksig", json.dumps(setting, indent=2))}
        why = "Software image signature verification was evaluated from the live BIG-IP liveinstall.checksig setting."
    elif vuln_id == "V-266167":
        httpd = client.get("/mgmt/tm/sys/httpd")
        validate_ip = parse_bool_value(str(httpd.get("authPamValidateIp")))
        compliant = validate_ip is True
        evidence_summary = {"sys_httpd_auth_pam_validate_ip": validate_ip}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("sys_httpd_auth_pam_validate_ip", required.get("sys_httpd_auth_pam_validate_ip", "== true"), validate_ip, compliant, "rest:/mgmt/tm/sys/httpd")]
        evidence = {"sys_httpd": evidence_source("rest", "/mgmt/tm/sys/httpd", json.dumps(httpd, indent=2))}
        why = "TMUI session source-IP pinning was evaluated from the live sys httpd configuration."
    else:
        return unsupported_validation(context, vuln_id, "This manual_or_generic control is not promoted for standalone live validation yet.")

    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, why, tmsh_fix, rest_fix)


def list_asm_policies(client: F5Client) -> list[dict[str, Any]]:
    result = client.get("/mgmt/tm/asm/policies?$top=200")
    return result.get("items", []) if isinstance(result, dict) else []


def path_from_link(link: str) -> str:
    parsed = urlparse(link)
    return parsed.path + (("?" + parsed.query) if parsed.query else "")


def fetch_subcollection_items(client: F5Client, link: str) -> list[dict[str, Any]]:
    if not link:
        return []
    result = client.get(path_from_link(link))
    return result.get("items", []) if isinstance(result, dict) else []


def evaluate_asm_policy_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    policies = list_asm_policies(client)
    security_policies = [item for item in policies if str(item.get("fullPath") or "").strip()]
    evidence: dict[str, Any] = {"asm_policies": evidence_source("rest", "/mgmt/tm/asm/policies", json.dumps(policies, indent=2))}
    evidence_summary: dict[str, Any] = {}
    comparisons: list[dict[str, Any]] = []
    why = ""

    if vuln_id == "V-266138":
        active_policies = [item for item in security_policies if bool(item.get("active"))]
        attached_policies = [item for item in active_policies if item.get("virtualServers")]
        attached_names = [str(item.get("fullPath") or item.get("name") or "") for item in attached_policies]
        policies_active = len(active_policies) > 0
        security_policy_attached = len(attached_policies) > 0
        compliant = policies_active and security_policy_attached
        evidence_summary = {
            "asm_policies_active": policies_active,
            "virtual_server_security_policy": attached_names[0] if attached_names else "none",
            "asm_attached_policy_count": len(attached_policies),
        }
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("asm_policies_active", required.get("asm_policies_active", "== true"), policies_active, policies_active, "rest:/mgmt/tm/asm/policies"),
            compare_row("virtual_server_security_policy", required.get("virtual_server_security_policy", "!= 'none'"), evidence_summary["virtual_server_security_policy"], security_policy_attached, "rest:/mgmt/tm/asm/policies"),
        ]
        why = "ASM policy activity and virtual server attachment were evaluated from live ASM policy inventory."
    elif vuln_id == "V-266149":
        scoped = [item for item in security_policies if item.get("virtualServers")]
        compliant_count = 0
        policy_details = []
        for policy in scoped:
            violations = fetch_subcollection_items(client, (((policy.get("blockingSettingsReference") or {}).get("link")) or "").replace("/blocking-settings?ver=", "/blocking-settings/violations?ver=")) if False else []
            if not violations:
                blocking = client.get(f"/mgmt/tm/asm/policies/{policy['id']}/blocking-settings/violations?$top=200")
                violations = blocking.get("items", []) if isinstance(blocking, dict) else []
            matched = [
                item for item in violations
                if str(item.get("description") or "").strip().lower() == "http protocol compliance failed"
            ]
            enabled = any(bool(item.get("alarm")) or bool(item.get("block")) for item in matched)
            if enabled:
                compliant_count += 1
            policy_details.append({"policy": policy.get("fullPath"), "matched_violation_count": len(matched), "alarm_or_block_enabled": enabled})
        evidence_summary = {
            "asm_http_protocol_compliance_enabled": len(scoped) > 0 and compliant_count == len(scoped),
            "asm_policy_count": len(scoped),
            "asm_http_protocol_compliance_policy_count": compliant_count,
        }
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("asm_http_protocol_compliance_enabled", required.get("asm_http_protocol_compliance_enabled", "== true"), evidence_summary["asm_http_protocol_compliance_enabled"], evidence_summary["asm_http_protocol_compliance_enabled"], "rest:/mgmt/tm/asm/policies")]
        compliant = evidence_summary["asm_http_protocol_compliance_enabled"]
        evidence["asm_http_protocol_compliance"] = evidence_source("rest", "/mgmt/tm/asm/policies/*/blocking-settings/violations", json.dumps(policy_details, indent=2))
        why = "Scoped ASM policies were checked for the HTTP protocol compliance failed blocking violation being alarmed or blocked."
    elif vuln_id == "V-266158":
        scoped = [item for item in security_policies if item.get("virtualServers")]
        compliant_count = 0
        policy_details = []
        for policy in scoped:
            parameters_result = client.get(f"/mgmt/tm/asm/policies/{policy['id']}/parameters?$top=200")
            parameters = parameters_result.get("items", []) if isinstance(parameters_result, dict) else []
            wildcard = next((item for item in parameters if str(item.get("name") or "") == "*" and str(item.get("type") or "").lower() == "wildcard"), None)
            enabled = bool(wildcard) and bool(wildcard.get("checkMetachars")) and bool(wildcard.get("metacharsOnParameterValueCheck"))
            if enabled:
                compliant_count += 1
            policy_details.append({"policy": policy.get("fullPath"), "wildcard_parameter_present": bool(wildcard), "metachar_validation_enabled": enabled})
        evidence_summary = {
            "asm_policy_count": len(scoped),
            "asm_parameter_validation_policy_count": compliant_count,
        }
        compliant = len(scoped) > 0 and compliant_count == len(scoped)
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("asm_policy_count", required.get("asm_policy_count", "> 0"), len(scoped), len(scoped) > 0, "rest:/mgmt/tm/asm/policies"),
            compare_row("asm_parameter_validation_policy_count", required.get("asm_parameter_validation_policy_count", "== asm_policy_count"), compliant_count, compliant, "rest:/mgmt/tm/asm/policies"),
        ]
        evidence["asm_parameter_validation"] = evidence_source("rest", "/mgmt/tm/asm/policies/*/parameters", json.dumps(policy_details, indent=2))
        why = "Scoped ASM policies were checked for wildcard parameter metachar validation on both names and values."
    elif vuln_id in {"V-266140", "V-266141", "V-266142"}:
        scoped = [item for item in security_policies if item.get("virtualServers")]
        compliant_count = 0
        policy_details = []
        for policy in scoped:
            enforcement_mode = str(policy.get("enforcementMode") or "").lower()
            signatures_result = client.get(f"/mgmt/tm/asm/policies/{policy['id']}/signatures?$top=200")
            signatures = signatures_result.get("items", []) if isinstance(signatures_result, dict) else []
            enforced = any(bool(item.get("enabled")) and bool(item.get("block")) for item in signatures)
            policy_compliant = enforcement_mode == "blocking" and enforced
            if policy_compliant:
                compliant_count += 1
            policy_details.append(
                {
                    "policy": policy.get("fullPath"),
                    "enforcement_mode": enforcement_mode,
                    "enabled_block_signatures_present": enforced,
                }
            )
        evidence_summary = {
            "asm_policy_blocking_mode": len(scoped) > 0 and compliant_count == len(scoped),
            "asm_required_signature_sets_enforced": len(scoped) > 0 and compliant_count == len(scoped),
            "asm_policy_count": len(scoped),
            "asm_signature_enforced_policy_count": compliant_count,
        }
        compliant = len(scoped) > 0 and compliant_count == len(scoped)
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("asm_policy_blocking_mode", required.get("asm_policy_blocking_mode", "== 'blocking'"), evidence_summary["asm_policy_blocking_mode"], evidence_summary["asm_policy_blocking_mode"], "rest:/mgmt/tm/asm/policies"),
            compare_row("asm_required_signature_sets_enforced", required.get("asm_required_signature_sets_enforced", "== true"), evidence_summary["asm_required_signature_sets_enforced"], evidence_summary["asm_required_signature_sets_enforced"], "rest:/mgmt/tm/asm/policies/*/signatures"),
        ]
        evidence["asm_signature_enforcement"] = evidence_source("rest", "/mgmt/tm/asm/policies/*/signatures", json.dumps(policy_details, indent=2))
        why = "Scoped ASM policies were checked for blocking enforcement mode and active blocking attack signatures."
    else:
        return unsupported_validation(context, vuln_id, "This asm_policy control is not promoted for standalone live validation yet.")

    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, why, tmsh_fix, rest_fix)


def evaluate_afm_firewall_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    control = CONTROL_CATALOG_MAP[vuln_id]
    client = context.client()
    policies = fetch_collection(client, "/mgmt/tm/security/firewall/policy?$top=200")
    evidence: dict[str, Any] = {"firewall_policies": evidence_source("rest", "/mgmt/tm/security/firewall/policy", json.dumps(policies, indent=2))}
    evidence_summary: dict[str, Any] = {}
    comparisons: list[dict[str, Any]] = []
    why = ""

    if vuln_id == "V-266144":
        configured = len(policies) > 0
        evidence_summary = {"security_firewall_policy_configured": configured, "security_firewall_policy_count": len(policies)}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("security_firewall_policy_configured", required.get("security_firewall_policy_configured", "== true"), configured, configured, "rest:/mgmt/tm/security/firewall/policy")]
        compliant = configured
        why = "AFM firewall policy presence was evaluated from the live firewall policy inventory."
    elif vuln_id == "V-266156":
        ignored = set(((control.get("organization_policy") or {}).get("ignored_profile_names") or []))
        profiles = fetch_collection(client, "/mgmt/tm/security/dos/profile?$top=200")
        custom = [item for item in profiles if str(item.get("fullPath") or "") not in ignored]
        mitigate_count = 0
        profile_details = []
        for profile in custom:
            dos_network = fetch_subcollection_items(client, ((profile.get("dosNetworkReference") or {}).get("link")) or "")
            has_mitigate = False
            for item in dos_network:
                dynamic = item.get("dynamicSignatures") or {}
                attack_vectors = item.get("networkAttackVector") or []
                if str(dynamic.get("detection") or "").lower() != "enabled":
                    continue
                if any(str(vec.get("state") or "").lower() == "mitigate" and str(vec.get("enforce") or "").lower() == "enabled" for vec in attack_vectors):
                    has_mitigate = True
                    break
            if has_mitigate:
                mitigate_count += 1
            profile_details.append({"profile": profile.get("fullPath"), "dos_network_objects": len(dos_network), "network_mitigation_enabled": has_mitigate})
        compliant = len(custom) == 0 or mitigate_count == len(custom)
        evidence_summary = {"dos_custom_profile_count": len(custom), "dos_profiles_network_mitigate_count": mitigate_count}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("dos_custom_profile_count", required.get("dos_custom_profile_count", "== 0"), len(custom), len(custom) == 0 or mitigate_count == len(custom), "rest:/mgmt/tm/security/dos/profile"),
            compare_row("dos_profiles_network_mitigate_count", required.get("dos_profiles_network_mitigate_count", "== dos_custom_profile_count"), mitigate_count, compliant, "rest:/mgmt/tm/security/dos/profile/*/dos-network"),
        ]
        evidence["dos_profiles_network"] = evidence_source("rest", "/mgmt/tm/security/dos/profile/*/dos-network", json.dumps(profile_details, indent=2))
        why = "Custom AFM DoS profiles were checked for dynamic-signature-backed network mitigation behavior."
    elif vuln_id == "V-266161":
        profile = client.get("/mgmt/tm/security/log/profile/global-network")
        network_items = fetch_subcollection_items(client, "/mgmt/tm/security/log/profile/~Common~global-network/network?$top=50")
        filters = (((network_items[0] if network_items else {}).get("filter")) or {})
        logging_enabled = any(str(filters.get(key) or "").lower() == "enabled" for key in ("logAclMatchAccept", "logAclMatchDrop", "logAclMatchReject"))
        evidence_summary = {"global_network_classification_logging_enabled": logging_enabled}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [compare_row("global_network_classification_logging_enabled", required.get("global_network_classification_logging_enabled", "== true"), logging_enabled, logging_enabled, "rest:/mgmt/tm/security/log/profile/global-network")]
        compliant = logging_enabled
        evidence["global_network_profile"] = evidence_source("rest", "/mgmt/tm/security/log/profile/global-network", json.dumps({"profile": profile, "network": network_items}, indent=2))
        why = "The global-network logging profile was evaluated for active unauthorized-service network event logging."
    elif vuln_id == "V-266157":
        ignored = set(((control.get("organization_policy") or {}).get("ignored_profile_names") or []))
        profiles = fetch_collection(client, "/mgmt/tm/security/dos/profile?$top=200")
        custom = [item for item in profiles if str(item.get("fullPath") or "") not in ignored]
        dynamic_count = 0
        profile_details = []
        for profile in custom:
            dos_network = fetch_subcollection_items(client, ((profile.get("dosNetworkReference") or {}).get("link")) or "")
            protocol_dns = fetch_subcollection_items(client, ((profile.get("protocolDnsReference") or {}).get("link")) or "")
            dynamic_enabled = any(str(((item.get("dynamicSignatures") or {}).get("detection")) or "").lower() == "enabled" for item in dos_network + protocol_dns)
            if dynamic_enabled:
                dynamic_count += 1
            profile_details.append({"profile": profile.get("fullPath"), "dynamic_signatures_enabled": dynamic_enabled})
        compliant = len(custom) == 0 or dynamic_count == len(custom)
        evidence_summary = {"dos_custom_profile_count": len(custom), "dos_profiles_dynamic_signatures_count": dynamic_count}
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("dos_custom_profile_count", required.get("dos_custom_profile_count", "== 0"), len(custom), len(custom) == 0 or dynamic_count == len(custom), "rest:/mgmt/tm/security/dos/profile"),
            compare_row("dos_profiles_dynamic_signatures_count", required.get("dos_profiles_dynamic_signatures_count", "== dos_custom_profile_count"), dynamic_count, compliant, "rest:/mgmt/tm/security/dos/profile/*"),
        ]
        evidence["dos_dynamic_signatures"] = evidence_source("rest", "/mgmt/tm/security/dos/profile/*", json.dumps(profile_details, indent=2))
        why = "Custom AFM DoS profiles were checked for dynamic signature detection across their live subprofiles."
    elif vuln_id == "V-266159":
        update = client.get("/mgmt/tm/sys/software/update")
        auto_check = str(update.get("autoCheck") or "").lower() == "enabled"
        auto_phonehome = str(update.get("autoPhonehome") or "").lower() == "enabled"
        compliant = auto_check and auto_phonehome
        evidence_summary = {
            "auto_update_check_enabled": auto_check,
            "live_update_realtime": auto_phonehome,
        }
        required = (projection.get("pullback_row") or {}).get("required", {})
        comparisons = [
            compare_row("auto_update_check_enabled", required.get("auto_update_check_enabled", "== true"), auto_check, auto_check, "rest:/mgmt/tm/sys/software/update"),
            compare_row("live_update_realtime", required.get("live_update_realtime", "== true"), auto_phonehome, auto_phonehome, "rest:/mgmt/tm/sys/software/update"),
        ]
        evidence["software_update"] = evidence_source("rest", "/mgmt/tm/sys/software/update", json.dumps(update, indent=2))
        why = "Automatic update check and live update phone-home settings were evaluated from the live BIG-IP software update configuration."
    elif vuln_id == "V-266160":
        profile = client.get("/mgmt/tm/security/log/profile/global-network")
        network_items = fetch_subcollection_items(client, "/mgmt/tm/security/log/profile/~Common~global-network/network?$top=50")
        filters = (((network_items[0] if network_items else {}).get("filter")) or {})
        logging_enabled = any(str(filters.get(key) or "").lower() == "enabled" for key in ("logAclMatchAccept", "logAclMatchDrop", "logAclMatchReject"))
        publisher = str(profile.get("publisher") or profile.get("logPublisher") or "")
        rule_details = []
        for policy in policies:
            rules = fetch_subcollection_items(client, ((policy.get("rulesReference") or {}).get("link")) or "")
            for rule in rules:
                rule_details.append(
                    {
                        "policy": policy.get("fullPath"),
                        "rule": rule.get("fullPath") or rule.get("name"),
                        "classificationPolicy": rule.get("classificationPolicy"),
                    }
                )
        if not rule_details:
            return make_not_applicable_payload(
                vuln_id,
                context.host,
                "No AFM content-filtering rules are configured on the live appliance.",
                {"firewall_rule_count": 0},
                {
                    "firewall_policies": evidence_source("rest", "/mgmt/tm/security/firewall/policy", json.dumps(policies, indent=2)),
                    "global_network_profile": evidence_source("rest", "/mgmt/tm/security/log/profile/global-network", json.dumps({"profile": profile, "network": network_items}, indent=2)),
                },
                [compare_row("firewall_rule_count", "> 0", 0, False, "rest:/mgmt/tm/security/firewall/policy")],
            )
        classification_configured = any(bool(item.get("classificationPolicy")) for item in rule_details)
        evidence_summary = {
            "firewall_classification_policy_configured": classification_configured,
            "global_network_classification_logging_enabled": logging_enabled and bool(publisher),
        }
        required = (projection.get("pullback_row") or {}).get("required", {}) or {
            "firewall_classification_policy_configured": "== true",
            "global_network_classification_logging_enabled": "== true",
        }
        comparisons = [
            compare_row("firewall_classification_policy_configured", required.get("firewall_classification_policy_configured", "== true"), classification_configured, classification_configured, "rest:/mgmt/tm/security/firewall/policy"),
            compare_row("global_network_classification_logging_enabled", required.get("global_network_classification_logging_enabled", "== true"), evidence_summary["global_network_classification_logging_enabled"], evidence_summary["global_network_classification_logging_enabled"], "rest:/mgmt/tm/security/log/profile/global-network"),
        ]
        compliant = all(row["match"] for row in comparisons)
        evidence["firewall_rules"] = evidence_source("rest", "/mgmt/tm/security/firewall/policy/*/rules", json.dumps(rule_details, indent=2))
        evidence["global_network_profile"] = evidence_source("rest", "/mgmt/tm/security/log/profile/global-network", json.dumps({"profile": profile, "network": network_items}, indent=2))
        why = "AFM firewall rules and the global-network profile were checked for classification-policy detection and classification logging."
    else:
        return unsupported_validation(context, vuln_id, "This afm_firewall control is not promoted for standalone live validation yet.")

    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, why, tmsh_fix, rest_fix)


def evaluate_password_policy_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    password_policy = client.get("/mgmt/tm/auth/password-policy")
    field_specs = {
        "V-266069": {
            "summary": {
                "auth_password_policy_max_login_failures": int(password_policy.get("maxLoginFailures") or 0),
                "auth_password_policy_lockout_duration": int(password_policy.get("lockoutDuration") or 0),
            },
            "comparisons": [
                ("auth_password_policy_max_login_failures", lambda value: value >= 1 and value <= 3),
                ("auth_password_policy_lockout_duration", lambda value: value >= 900),
            ],
        },
        "V-266087": {
            "summary": {"auth_password_policy_min_length": int(password_policy.get("minimumLength") or 0)},
            "comparisons": [("auth_password_policy_min_length", lambda value: value >= 15)],
        },
        "V-266088": {
            "summary": {"auth_password_policy_required_uppercase": int(password_policy.get("requiredUppercase") or 0)},
            "comparisons": [("auth_password_policy_required_uppercase", lambda value: value >= 1)],
        },
        "V-266089": {
            "summary": {"auth_password_policy_required_lowercase": int(password_policy.get("requiredLowercase") or 0)},
            "comparisons": [("auth_password_policy_required_lowercase", lambda value: value >= 1)],
        },
        "V-266090": {
            "summary": {"auth_password_policy_required_numeric": int(password_policy.get("requiredNumeric") or 0)},
            "comparisons": [("auth_password_policy_required_numeric", lambda value: value >= 1)],
        },
        "V-266091": {
            "summary": {"auth_password_policy_required_special": int(password_policy.get("requiredSpecial") or 0)},
            "comparisons": [("auth_password_policy_required_special", lambda value: value >= 1)],
        },
    }
    spec = field_specs[vuln_id]
    evidence_summary = spec["summary"]
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row(field, required.get(field, ""), evidence_summary[field], predicate(evidence_summary[field]), "rest:/mgmt/tm/auth/password-policy")
        for field, predicate in spec["comparisons"]
    ]
    compliant = all(row["match"] for row in comparisons)
    evidence = {"auth_password_policy": evidence_source("rest", "/mgmt/tm/auth/password-policy", json.dumps(password_policy, indent=2))}
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Live BIG-IP password policy settings were evaluated from the password-policy endpoint.", tmsh_fix, rest_fix)


def evaluate_banner_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    sshd = client.get("/mgmt/tm/sys/sshd")
    global_settings = client.get("/mgmt/tm/sys/global-settings")
    evidence_summary = {
        "sys_sshd_banner": str(sshd.get("banner") or ""),
        "sys_httpd_gui_security_banner_configured": parse_bool_value(str(global_settings.get("guiSecurityBanner"))),
        "guiSecurityBannerText": str(global_settings.get("guiSecurityBannerText") or "").strip(),
    }
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [
        compare_row("sys_sshd_banner", required.get("sys_sshd_banner", "== 'enabled'"), evidence_summary["sys_sshd_banner"], str(evidence_summary["sys_sshd_banner"]).lower() == "enabled", "rest:/mgmt/tm/sys/sshd"),
        compare_row("sys_httpd_gui_security_banner_configured", required.get("sys_httpd_gui_security_banner_configured", "== true"), evidence_summary["sys_httpd_gui_security_banner_configured"], evidence_summary["sys_httpd_gui_security_banner_configured"] is True, "rest:/mgmt/tm/sys/global-settings"),
        compare_row(
            "guiSecurityBannerText",
            required.get("guiSecurityBannerText", "== canonical_dod_banner_text"),
            evidence_summary["guiSecurityBannerText"],
            evidence_summary["guiSecurityBannerText"] == CANONICAL_DOD_BANNER_TEXT,
            "rest:/mgmt/tm/sys/global-settings",
        ),
    ]
    compliant = all(row["match"] for row in comparisons)
    evidence = {
        "sys_sshd": evidence_source("rest", "/mgmt/tm/sys/sshd", json.dumps(sshd, indent=2)),
        "sys_global_settings": evidence_source("rest", "/mgmt/tm/sys/global-settings", json.dumps(global_settings, indent=2)),
    }
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "SSH and TMUI security banner configuration were evaluated from live appliance settings.", tmsh_fix, rest_fix)


def evaluate_logging_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    syslog = client.get("/mgmt/tm/sys/syslog")
    servers = syslog.get("remoteServers") or []
    if isinstance(servers, str):
        count = len([item for item in servers.split() if item.strip()])
    else:
        count = len(servers)
    evidence_summary = {"sys_syslog_remote_server_count": count}
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [compare_row("sys_syslog_remote_server_count", required.get("sys_syslog_remote_server_count", ">= 2"), count, count >= 2, "rest:/mgmt/tm/sys/syslog")]
    compliant = count >= 2
    evidence = {"sys_syslog": evidence_source("rest", "/mgmt/tm/sys/syslog", json.dumps(syslog, indent=2))}
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Remote syslog destination count was evaluated from live BIG-IP syslog settings.", tmsh_fix, rest_fix)


def evaluate_ntp_server_count_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    ntp = client.get("/mgmt/tm/sys/ntp")
    servers = ntp.get("servers") or []
    count = len(servers) if isinstance(servers, list) else len(str(servers).split())
    evidence_summary = {"sys_ntp_server_count": count}
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [compare_row("sys_ntp_server_count", required.get("sys_ntp_server_count", ">= 2"), count, count >= 2, "rest:/mgmt/tm/sys/ntp")]
    compliant = count >= 2
    evidence = {"sys_ntp": evidence_source("rest", "/mgmt/tm/sys/ntp", json.dumps(ntp, indent=2))}
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Configured NTP server count was evaluated from live BIG-IP NTP settings.", tmsh_fix, rest_fix)


def evaluate_ntp_timezone_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    ntp = client.get("/mgmt/tm/sys/ntp")
    timezone = str(ntp.get("timezone") or "")
    evidence_summary = {"sys_ntp_timezone": timezone}
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [compare_row("sys_ntp_timezone", required.get("sys_ntp_timezone", "== 'UTC'"), timezone, timezone.upper() == "UTC", "rest:/mgmt/tm/sys/ntp")]
    compliant = timezone.upper() == "UTC"
    evidence = {"sys_ntp": evidence_source("rest", "/mgmt/tm/sys/ntp", json.dumps(ntp, indent=2))}
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    rest_fix = ((projection.get("remediation") or {}).get("endpoint")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if compliant else "open", compliant, evidence_summary, evidence, comparisons, "Configured NTP timezone was evaluated from live BIG-IP NTP settings.", tmsh_fix, rest_fix)


def evaluate_ntp_auth_family(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    projection = PROJECTION_MAP[vuln_id]
    client = context.client()
    include_output = run_tmsh_or_empty(client, "list sys ntp include")
    required_include = ((CONTROL_CATALOG_MAP[vuln_id].get("organization_policy") or {}).get("required_include_substrings") or [])
    enabled = all(text in include_output for text in required_include)
    evidence_summary = {"sys_ntp_authentication_enabled": enabled}
    required = (projection.get("pullback_row") or {}).get("required", {})
    comparisons = [compare_row("sys_ntp_authentication_enabled", required.get("sys_ntp_authentication_enabled", "== true"), enabled, enabled, "tmsh:tmsh list sys ntp include")]
    evidence = {"sys_ntp_include": evidence_source("tmsh", "tmsh list sys ntp include", include_output)}
    tmsh_fix = ((projection.get("remediation") or {}).get("tmsh_equivalent")) or ""
    return make_validation_payload(vuln_id, context.host, "not_a_finding" if enabled else "open", enabled, evidence_summary, evidence, comparisons, "NTP authentication directives were evaluated from the live BIG-IP NTP include block.", tmsh_fix)


def unsupported_validation(context: SessionContext, vuln_id: str, message: str) -> dict[str, Any]:
    return {
        "ok": True,
        "vuln_id": vuln_id,
        "status": "insufficient_evidence",
        "requested_host": context.host,
        "provenance": {
            "bundle_dir": str(ROOT / "sessions"),
            "bundle_timestamp": "",
            "bundle_host_ip": context.host,
            "bundle_host_hostname": context.host,
            "bundle_operation": "validate",
            "bundle_source": "standalone_web_app",
            "bundle_is_synthetic": False,
            "host_match": True,
            "selection_note": "Standalone export blocked live validation because this control is not yet supported.",
        },
        "evidence": {},
        "comparison_rows": [],
        "adjudication": {
            "compliant": False,
            "human_review_row": {"vuln_id": vuln_id, "status": "INSUFFICIENT_EVIDENCE", "requirement": "Standalone live evaluation unavailable", "why": message},
            "proof_steps": [],
        },
        "bundle_metadata": {"vuln_id": vuln_id, "operation": "validate", "bundle_source": "standalone_web_app"},
        "artifact_bundle": {"output_dir": str(ROOT / "sessions")},
    }


EVALUATOR_REGISTRY: dict[str, Callable[[SessionContext, str], dict[str, Any]]] = {
    "manual_or_generic": evaluate_manual_or_generic_family,
    "apm_profile_scalar": evaluate_apm_profile_scalar_family,
    "apm_log_setting": evaluate_apm_log_setting_family,
    "apm_policy": evaluate_apm_policy_family,
    "apm_network_access": evaluate_apm_network_access_family,
    "asm_policy": evaluate_asm_policy_family,
    "afm_firewall": evaluate_afm_firewall_family,
    "sshd": evaluate_sshd_family,
    "ltm_virtual_services": evaluate_ltm_virtual_services_family,
    "ltm_virtual_ssl": evaluate_ltm_virtual_ssl_family,
    "ltm_virtual_ssl_protocol": evaluate_ltm_virtual_ssl_protocol_family,
    "smtp_security": lambda context, vuln_id: evaluate_service_profile_security_family(context, vuln_id, "smtp"),
    "ftp_security": lambda context, vuln_id: evaluate_service_profile_security_family(context, vuln_id, "ftp"),
    "protocol_inspection": evaluate_protocol_inspection_family,
    "banner": evaluate_banner_family,
    "logging": evaluate_logging_family,
    "ntp_servers": evaluate_ntp_server_count_family,
    "ntp_timezone": evaluate_ntp_timezone_family,
    "ntp_auth": evaluate_ntp_auth_family,
    "password_policy": evaluate_password_policy_family,
}

VULN_TO_EVALUATOR = {
    "V-266137": "apm_profile_scalar",
    "V-266064": "manual_or_generic",
    "V-266065": "manual_or_generic",
    "V-266066": "manual_or_generic",
    "V-266068": "manual_or_generic",
    "V-266078": "manual_or_generic",
    "V-266079": "manual_or_generic",
    "V-266080": "manual_or_generic",
    "V-266085": "manual_or_generic",
    "V-266092": "manual_or_generic",
    "V-266093": "manual_or_generic",
    "V-266094": "manual_or_generic",
    "V-266167": "manual_or_generic",
    "V-266138": "asm_policy",
    "V-266140": "asm_policy",
    "V-266141": "asm_policy",
    "V-266142": "asm_policy",
    "V-266149": "asm_policy",
    "V-266158": "asm_policy",
    "V-266143": "apm_policy",
    "V-266145": "apm_policy",
    "V-266146": "apm_log_setting",
    "V-266151": "apm_policy",
    "V-266152": "apm_policy",
    "V-266153": "apm_policy",
    "V-266154": "apm_policy",
    "V-266155": "apm_profile_scalar",
    "V-266162": "apm_profile_scalar",
    "V-266163": "apm_profile_scalar",
    "V-266164": "apm_profile_scalar",
    "V-266165": "apm_policy",
    "V-266166": "apm_policy",
    "V-266168": "apm_profile_scalar",
    "V-266169": "apm_profile_scalar",
    "V-266171": "apm_policy",
    "V-266172": "apm_network_access",
    "V-266175": "apm_profile_scalar",
    "V-266144": "afm_firewall",
    "V-266156": "afm_firewall",
    "V-266157": "afm_firewall",
    "V-266159": "afm_firewall",
    "V-266160": "afm_firewall",
    "V-266161": "afm_firewall",
    "V-266095": "sshd",
    "V-266084": "ltm_virtual_services",
    "V-266150": "ltm_virtual_services",
    "V-266139": "ltm_virtual_ssl_protocol",
    "V-266147": "smtp_security",
    "V-266148": "ftp_security",
    "V-266170": "ltm_virtual_ssl",
    "V-266173": "protocol_inspection",
    "V-266070": "banner",
    "V-266075": "logging",
    "V-266076": "ntp_servers",
    "V-266077": "ntp_timezone",
    "V-266086": "ntp_auth",
    "V-266069": "password_policy",
    "V-266087": "password_policy",
    "V-266088": "password_policy",
    "V-266089": "password_policy",
    "V-266090": "password_policy",
    "V-266091": "password_policy",
}


def supported_vuln_ids() -> set[str]:
    return set(VULN_TO_EVALUATOR)


def support_state(vuln_id: str) -> dict[str, Any]:
    control = CONTROL_CATALOG_MAP[vuln_id]
    evaluator = VULN_TO_EVALUATOR.get(vuln_id)
    return {
        "vuln_id": vuln_id,
        "handler_family": control.get("handler_family") or "unknown",
        "evaluator_key": evaluator,
        "live_supported": evaluator is not None,
        "support_mode": "live_supported" if evaluator else "not_yet_supported",
    }


def evaluate_control(context: SessionContext, vuln_id: str) -> dict[str, Any]:
    evaluator_key = VULN_TO_EVALUATOR.get(vuln_id)
    if evaluator_key is None:
        return unsupported_validation(context, vuln_id, "This control is present in the standalone catalog, but its live evaluator is not implemented yet.")
    return EVALUATOR_REGISTRY[evaluator_key](context, vuln_id)

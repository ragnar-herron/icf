"""Backend-only STIG validation bundle producer for the governed export UI.

The browser is not allowed to interpret raw appliance evidence.  This module
is the export-local backend adapter that turns canonical control contracts and
live F5 observations into typed, render-safe bundles containing only atomic
comparison rows.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from capture_runner import capture_raw_evidence, normalize_with_recipe, recipe_for_vid
from f5_client import F5Client


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CATALOG = DATA / "ControlCatalog.json"
FACTORY_BUNDLE = DATA / "FactoryDistinctionBundle.json"

PARTITION_CLASSES = frozenset({
    "compliant", "noncompliant", "disabled",
    "absent", "malformed", "indeterminate",
})

FIXTURE_CLASSES = (
    "good_minimal", "bad_canonical", "bad_representation_variant",
    "boundary_value", "disabled_state", "absent_state",
    "malformed_state", "noisy_evidence", "out_of_scope_variant",
)


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_catalog() -> dict[str, dict[str, Any]]:
    doc = json.loads(CATALOG.read_text(encoding="utf-8"))
    return {
        item["vuln_id"]: item
        for item in doc.get("controls", [])
        if isinstance(item, dict) and item.get("vuln_id")
    }


_factory_bundle_cache: dict[str, Any] | None = None


def load_factory_bundle() -> dict[str, Any]:
    """Load the Rust-generated FactoryDistinctionBundle.

    The bundle contains pre-evaluated fixture rows for all 67 controls,
    DP gate results, bindings, partitions, and equivalence classes.
    The Python export projects these artifacts rather than re-evaluating.
    """
    global _factory_bundle_cache
    if _factory_bundle_cache is not None:
        return _factory_bundle_cache
    doc = json.loads(FACTORY_BUNDLE.read_text(encoding="utf-8"))
    rows_by_vid: dict[str, list[dict[str, Any]]] = {}
    for r in doc.get("evaluatedRows", []):
        vid = r.get("measurable_id", "")
        rows_by_vid.setdefault(vid, []).append(r)
    bindings_by_vid: dict[str, dict[str, Any]] = {}
    for b in doc.get("bindings", []):
        bindings_by_vid[b.get("contract_measurable_id", "")] = b
    recipes_by_vid: dict[str, dict[str, Any]] = {}
    for recipe in doc.get("captureRecipes", []):
        recipes_by_vid[recipe.get("measurable_id", "")] = recipe
    doc["_rowsByVid"] = rows_by_vid
    doc["_bindingsByVid"] = bindings_by_vid
    doc["_recipesByVid"] = recipes_by_vid
    _factory_bundle_cache = doc
    return doc


def factory_rows_for_vid(vid: str) -> list[dict[str, Any]]:
    """Return projected atomic comparison rows for a V-ID from the factory bundle."""
    bundle = load_factory_bundle()
    factory_rows = bundle.get("_rowsByVid", {}).get(vid, [])
    binding = bundle.get("_bindingsByVid", {}).get(vid, {})
    projected: list[dict[str, Any]] = []
    for fr in factory_rows:
        verdict_raw = fr.get("verdict", "Unresolved")
        verdict = verdict_raw.lower() if isinstance(verdict_raw, str) else "unresolved"
        partition_class = {
            "pass": "compliant",
            "fail": "noncompliant",
        }.get(verdict, "indeterminate")
        unresolved_reason = fr.get("unresolved_reason") or ""
        if verdict == "unresolved":
            if "disabled" in unresolved_reason.lower() or "disabled" in fr.get("row_id", "").lower():
                partition_class = "disabled"
            elif "absent" in fr.get("row_id", "").lower() or "missing" in unresolved_reason.lower():
                partition_class = "absent"
            elif "malformed" in fr.get("row_id", "").lower():
                partition_class = "malformed"
        projected.append({
            "measurableId": fr.get("measurable_id", vid),
            "requiredAtomic": fr.get("required_atomic", binding.get("required_atomic_description", "")),
            "observedAtomic": fr.get("observed_atomic", ""),
            "operator": fr.get("comparison_operator", "factory"),
            "verdict": verdict,
            "evidenceSource": f"factory::{fr.get('row_id', '')}",
            "comparisonExpression": fr.get("comparison_operator", ""),
            "partitionClass": partition_class,
        })
    return projected


def factory_binding_for_vid(vid: str) -> dict[str, Any]:
    return load_factory_bundle().get("_bindingsByVid", {}).get(vid, {})


def factory_recipe_for_vid(vid: str) -> dict[str, Any] | None:
    return load_factory_bundle().get("_recipesByVid", {}).get(vid)


def first_match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.I | re.M)
    return match.group(1).strip() if match else None


def first_int(text: str, pattern: str) -> int | None:
    value = first_match(text, pattern)
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


def positive_lte(value: int | None, maximum: int) -> bool:
    return value is not None and 0 < value <= maximum


SERVICE_PORTS = {
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
    tail = re.sub(r"%\d+", "", tail)
    candidates: list[str] = []
    if ":" in tail:
        candidates.append(tail.rsplit(":", 1)[-1])
    if "." in tail:
        candidates.append(tail.rsplit(".", 1)[-1])
    candidates.append(tail)
    for candidate in candidates:
        normalized = candidate.strip().lower()
        if normalized in SERVICE_PORTS:
            return SERVICE_PORTS[normalized]
        if normalized.isdigit():
            return str(int(normalized))
    return ""


def extract_tmsh_named_block_items(text: str, block_name: str) -> list[str]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.match(rf"^\s+{re.escape(block_name)}\s+\{{", line):
            depth = 1
            items: list[str] = []
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


def parse_ltm_virtual_services(text: str) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    matches = list(re.finditer(r"(?m)^ltm virtual\s+(\S+)\s+\{", text))
    for index, match in enumerate(matches):
        name = match.group(1).rsplit("/", 1)[-1]
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        destination = first_match(body, r"^\s+destination\s+(\S+)") or ""
        services.append(
            {
                "name": name,
                "destination": destination,
                "port": destination_port(destination),
                "ip_protocol": (first_match(body, r"^\s+ip-protocol\s+(\S+)") or "any").lower(),
                "enabled": not re.search(r"(?m)^\s+disabled\s*$", body),
                "profiles": sorted(set(extract_tmsh_named_block_items(body, "profiles"))),
            }
        )
    return services


def profile_short_name(name: str) -> str:
    return str(name or "").strip().rsplit("/", 1)[-1].lower()


def parse_client_ssl_profiles(text: str) -> dict[str, dict[str, str]]:
    profiles: dict[str, dict[str, str]] = {}
    matches = list(re.finditer(r"(?m)^ltm profile client-ssl\s+(\S+)\s+\{", text))
    for index, match in enumerate(matches):
        name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end]
        cipher_match = re.search(r"(?m)^\s+ciphers\s+(.+?)\s*$", body)
        profiles[profile_short_name(name)] = {
            "name": name,
            "ciphers": (cipher_match.group(1) if cipher_match else "").strip().strip('"'),
        }
    return profiles


def cipher_marker_present(ciphers: str, marker: str) -> bool:
    cipher_text = str(ciphers or "").lower()
    wanted = str(marker or "").lower()
    if wanted in cipher_text:
        return True
    return bool(re.search(re.escape(wanted).replace(r"\+", r".*"), cipher_text))


def strong_cipher_requirement(policy: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    strong = (((policy.get("client_ssl_requirements") or {}).get("strong_cipher") or {}))
    markers = [str(m).lower() for m in strong.get("required_cipher_markers_any", [])]
    prefixes = [str(p).lower() for p in strong.get("required_cipher_prefixes_any", [])]
    parts: list[str] = []
    if markers:
        parts.append("cipher contains any of {" + ", ".join(markers) + "}")
    if prefixes:
        parts.append("cipher expression starts with any of {" + ", ".join(prefixes) + "}")
    return " OR ".join(parts), markers, prefixes


def is_strong_cipher(ciphers: str, markers: list[str], prefixes: list[str]) -> bool:
    lowered = str(ciphers or "").lower()
    return any(lowered.startswith(prefix) for prefix in prefixes) or any(
        cipher_marker_present(lowered, marker) for marker in markers
    )


def _infer_partition(verdict: str, partition_class: str | None) -> str:
    if partition_class and partition_class in PARTITION_CLASSES:
        return partition_class
    return {"pass": "compliant", "fail": "noncompliant"}.get(verdict, "indeterminate")


def row(
    measurable: str,
    required: str,
    observed: Any,
    match: bool | None,
    source: str,
    operator: str,
    expression: str,
    partition_class: str | None = None,
) -> dict[str, Any]:
    verdict = "unresolved" if match is None else ("pass" if match else "fail")
    return {
        "measurableId": measurable,
        "requiredAtomic": required,
        "observedAtomic": observed,
        "operator": operator,
        "verdict": verdict,
        "evidenceSource": source,
        "comparisonExpression": expression,
        "partitionClass": _infer_partition(verdict, partition_class),
    }


def status_from_rows(rows: list[dict[str, Any]]) -> str:
    if rows and all(item.get("operator") == "projected_unresolved" for item in rows):
        return "projected_unresolved"
    if any(item.get("verdict") == "unresolved" for item in rows):
        return "insufficient_evidence"
    return "open" if any(item.get("verdict") == "fail" for item in rows) else "not_a_finding"


def partition_summary(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {cls: 0 for cls in sorted(PARTITION_CLASSES)}
    for r in rows:
        cls = r.get("partitionClass", "indeterminate")
        counts[cls] = counts.get(cls, 0) + 1
    return counts


def capture_for_control(client: F5Client, control: dict[str, Any]) -> dict[str, str]:
    if not is_promoted(str(control.get("vuln_id") or "")):
        return capture_raw_evidence(client, control)
    commands = set(control.get("tmsh_commands") or [])
    family = control.get("handler_family", "")
    if control.get("vuln_id") in {"V-266084", "V-266150"} or family == "ltm_virtual_services":
        commands.add("tmsh list ltm virtual all-properties")
    if control.get("vuln_id") == "V-266170" or "ltm_profile_client_ssl_strong_cipher_count" in (control.get("evidence_required") or []):
        commands.add("tmsh list ltm profile client-ssl all-properties")
        commands.add("tmsh list ltm virtual all-properties")
    if control.get("vuln_id") == "V-266095":
        commands.update(
            {
                "tmsh list sys httpd all-properties",
                "tmsh list cli global-settings all-properties",
                "tmsh list sys global-settings all-properties",
            }
        )
    evidence: dict[str, str] = {}
    for command in sorted(commands):
        try:
            evidence[command] = client.run_tmsh(command)
        except Exception as exc:  # noqa: BLE001 - unavailable evidence is explicit.
            evidence[command] = json.dumps({"available": False, "error": str(exc)})
    if control.get("vuln_id") == "V-266095":
        try:
            evidence["/mgmt/tm/sys/sshd"] = json.dumps(client.get("/mgmt/tm/sys/sshd"))
        except Exception as exc:  # noqa: BLE001
            evidence["/mgmt/tm/sys/sshd"] = json.dumps({"available": False, "error": str(exc)})
    return evidence


def evaluate_virtual_services(control: dict[str, Any], evidence: dict[str, str]) -> list[dict[str, Any]]:
    policy = control.get("organization_policy") or {}
    disallowed = {str(int(p)) for p in policy.get("disallowed_destination_ports", [])}
    services = parse_ltm_virtual_services(evidence.get("tmsh list ltm virtual all-properties", ""))
    disabled_count = sum(1 for s in services if not s["enabled"])
    rows: list[dict[str, Any]] = []
    for service in services:
        if not service["enabled"]:
            continue
        port = str(service["port"])
        ok = None if port == "" else port not in disallowed
        rows.append(
            row(
                f"ltm_virtual.{service['name']}.destination_port",
                "not in {" + ", ".join(sorted(disallowed, key=int)) + "}",
                port,
                ok,
                "tmsh:list ltm virtual all-properties",
                "set_not_contains" if ok is not None else "unresolved_parse",
                f"port {port or 'unparsed'} not in disallowed destination ports",
            )
        )
    if not rows and disabled_count > 0:
        rows.append(row(
            "ltm_virtual.enabled_listener_count",
            ">= 1 enabled listener",
            0,
            None,
            "tmsh:list ltm virtual all-properties",
            "disabled_state",
            f"all {disabled_count} virtual server(s) disabled; cannot evaluate",
            partition_class="disabled",
        ))
    elif not rows and not services:
        rows.append(row(
            "ltm_virtual.enabled_listener_count",
            ">= 1 virtual server present",
            None,
            None,
            "tmsh:list ltm virtual all-properties",
            "absent",
            "no virtual server evidence found",
            partition_class="absent",
        ))
    elif not rows:
        rows.append(row("ltm_virtual.enabled_listener_count", "0 disallowed listeners", 0, True, "tmsh:list ltm virtual all-properties", "equals", "0 == 0"))
    return rows


def evaluate_v266095(evidence: dict[str, str]) -> list[dict[str, Any]]:
    httpd = evidence.get("tmsh list sys httpd all-properties", "")
    cli = evidence.get("tmsh list cli global-settings all-properties", "")
    global_settings = evidence.get("tmsh list sys global-settings all-properties", "")
    try:
        sshd_payload = json.loads(evidence.get("/mgmt/tm/sys/sshd", "{}"))
    except json.JSONDecodeError:
        sshd_payload = {}

    all_absent = not httpd and not cli and not global_settings and not sshd_payload
    values = [
        ("sys_httpd_auth_pam_idle_timeout", "> 0 AND <= 300", first_int(httpd, r"\bauth-pam-idle-timeout\s+(\d+)"), 300, "tmsh:list sys httpd all-properties"),
        ("cli_global_settings_idle_timeout", "> 0 AND <= 5", first_int(cli, r"\bidle-timeout\s+(\d+)"), 5, "tmsh:list cli global-settings all-properties"),
        ("sys_global_settings_console_inactivity_timeout", "> 0 AND <= 300", first_int(global_settings, r"\bconsole-inactivity-timeout\s+(\d+)"), 300, "tmsh:list sys global-settings all-properties"),
        ("sys_sshd_inactivity_timeout", "> 0 AND <= 300", sshd_payload.get("inactivityTimeout"), 300, "rest:/mgmt/tm/sys/sshd"),
    ]
    rows = []
    for measurable, required, observed, maximum, source in values:
        try:
            numeric = int(observed)
        except (TypeError, ValueError):
            numeric = None
        if numeric is None and all_absent:
            rows.append(row(measurable, required, None, None, source, "absent", f"no evidence for {measurable}", partition_class="absent"))
        else:
            rows.append(row(measurable, required, numeric, positive_lte(numeric, maximum), source, "positive_lte", f"0 < {numeric if numeric is not None else 'null'} <= {maximum}"))
    if all_absent:
        rows.append(row("sys_httpd_auth_pam_dashboard_timeout", "on", None, None, "tmsh:list sys httpd all-properties", "absent", "no evidence for dashboard timeout", partition_class="absent"))
    else:
        dashboard_on = "auth-pam-dashboard-timeout on" in httpd.lower()
        rows.append(row("sys_httpd_auth_pam_dashboard_timeout", "on", "on" if dashboard_on else "off", dashboard_on, "tmsh:list sys httpd all-properties", "equals", f"{'on' if dashboard_on else 'off'} == on"))
    return rows


def evaluate_v266170(control: dict[str, Any], evidence: dict[str, str]) -> list[dict[str, Any]]:
    virtuals = parse_ltm_virtual_services(evidence.get("tmsh list ltm virtual all-properties", ""))
    profiles = parse_client_ssl_profiles(evidence.get("tmsh list ltm profile client-ssl all-properties", ""))
    disabled_count = sum(1 for s in virtuals if not s["enabled"])
    attached = sorted(
        {
            profile_short_name(profile)
            for service in virtuals
            if service["enabled"]
            for profile in service["profiles"]
            if profile_short_name(profile) in profiles or "ssl" in profile_short_name(profile)
        }
    )

    if not virtuals:
        return [row(
            "ltm_attached_client_ssl_profile_count",
            ">= 1 virtual server present",
            None,
            None,
            "tmsh:list ltm virtual all-properties",
            "absent",
            "no virtual server evidence found",
            partition_class="absent",
        )]

    if not attached and disabled_count > 0 and not any(s["enabled"] for s in virtuals):
        return [row(
            "ltm_attached_client_ssl_profile_count",
            ">= 1 enabled virtual with ssl profile",
            0,
            None,
            "tmsh:list ltm virtual all-properties",
            "disabled_state",
            f"all {disabled_count} virtual server(s) disabled; cannot evaluate cipher strength",
            partition_class="disabled",
        )]

    required, markers, prefixes = strong_cipher_requirement(control.get("organization_policy") or {})
    strong_names = [
        name for name in attached
        if name in profiles and is_strong_cipher(profiles[name].get("ciphers", ""), markers, prefixes)
    ]
    pass_counts = len(attached) == 0 or len(strong_names) == len(attached)
    rows = [
        row("ltm_attached_client_ssl_profile_count", "== 0 OR strong_cipher_count == attached_count", len(attached), pass_counts, "tmsh:list ltm virtual all-properties", "count_relation", f"{len(attached)} == 0 OR {len(strong_names)} == {len(attached)}"),
        row("ltm_profile_client_ssl_strong_cipher_count", f"== {len(attached)}", len(strong_names), pass_counts, "tmsh:list ltm profile client-ssl all-properties", "equals", f"{len(strong_names)} == {len(attached)}"),
    ]
    for name in attached:
        observed = profiles.get(name, {}).get("ciphers", "profile not found")
        ok = name in strong_names
        rows.append(row(f"ltm_profile_client_ssl.{name}.cipher_expression", required, observed, ok, "tmsh:list ltm profile client-ssl all-properties", "lawful_cipher_match", f"profile {name} cipher expression satisfies ({required})"))
    return rows


PROMOTED_LIVE_VIDS = frozenset({"V-266084", "V-266095", "V-266150", "V-266170"})


def is_promoted(vid: str) -> bool:
    return vid in PROMOTED_LIVE_VIDS


def _field_order_for_vid(vid: str) -> list[str]:
    recipe = factory_recipe_for_vid(vid)
    if recipe:
        return [str(rule.get("field") or "") for rule in recipe.get("extraction_rules", []) if str(rule.get("field") or "")]
    return []


def _quoted_token(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return ""
    return str(value).strip().strip('"').strip("'")


def _org_defined_literal(binding: dict[str, Any]) -> str | None:
    value = binding.get("org_defined_value")
    if not isinstance(value, dict) or len(value) != 1:
        return None
    inner = next(iter(value.values()))
    return _quoted_token(inner)


def _required_atomic_for_vid(vid: str) -> str:
    binding = factory_binding_for_vid(vid)
    return str(binding.get("required_atomic_description") or "canonical adapter fixture")


def _operator_for_vid(vid: str) -> str:
    rows = load_factory_bundle().get("_rowsByVid", {}).get(vid, [])
    if rows:
        return str(rows[0].get("comparison_operator") or "factory_projection")
    return "factory_projection"


def _predicate_texts(binding: dict[str, Any]) -> tuple[str | None, str | None]:
    note = str(binding.get("adapter_interpretation_note") or "")
    pass_match = re.search(r"Pass predicate:\s*`([^`]+)`", note)
    fail_match = re.search(r"Fail predicate:\s*`([^`]+)`", note)
    return (
        pass_match.group(1).strip() if pass_match else None,
        fail_match.group(1).strip() if fail_match else None,
    )


def _coerce_for_compare(value: str | None, expected_literal: str) -> int | str | bool | None:
    if value is None:
        return None
    expected = expected_literal.strip()
    candidate = _quoted_token(value)
    lowered_expected = expected.lower()
    if lowered_expected in {"true", "false"}:
        lowered_candidate = candidate.lower()
        if lowered_candidate in {"true", "false"}:
            return lowered_candidate == "true"
        return None
    if re.fullmatch(r"-?\d+", expected):
        if re.fullmatch(r"-?\d+", candidate):
            return int(candidate)
        return None
    return candidate


def _parse_clause(clause: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"([A-Za-z0-9_]+)\s*(==|!=|<=|>=|<|>)\s*(.+)", clause.strip())
    if not match:
        raise RuntimeError(f"unsupported predicate clause: {clause}")
    field, operator, expected = match.groups()
    return field, operator, expected.strip()


def _evaluate_clause(field_map: dict[str, str], binding: dict[str, Any], clause: str) -> bool | None:
    field, operator, expected = _parse_clause(clause)
    observed_raw = field_map.get(field)
    if observed_raw is None:
        return None
    if expected == "org_defined_value":
        org_defined = _org_defined_literal(binding)
        if org_defined is None:
            return None
        expected = org_defined
    expected = expected.strip().strip("`")
    if (expected.startswith("'") and expected.endswith("'")) or (expected.startswith('"') and expected.endswith('"')):
        expected = expected[1:-1]
    observed = _coerce_for_compare(observed_raw, expected)
    typed_expected = _coerce_for_compare(expected, expected)
    if observed is None or typed_expected is None:
        return None
    if operator == "==":
        return observed == typed_expected
    if operator == "!=":
        return observed != typed_expected
    if operator == "<=":
        return bool(observed <= typed_expected)
    if operator == ">=":
        return bool(observed >= typed_expected)
    if operator == "<":
        return bool(observed < typed_expected)
    if operator == ">":
        return bool(observed > typed_expected)
    return None


def _evaluate_predicate(field_map: dict[str, str], binding: dict[str, Any], predicate: str | None) -> bool | None:
    if not predicate:
        return None
    or_groups = [group.strip() for group in predicate.split(" OR ")]
    saw_unresolved = False
    for group in or_groups:
        and_clauses = [clause.strip() for clause in group.split(" AND ")]
        group_values: list[bool | None] = [
            _evaluate_clause(field_map, binding, clause) for clause in and_clauses
        ]
        if any(value is False for value in group_values):
            continue
        if any(value is None for value in group_values):
            saw_unresolved = True
            continue
        return True
    return None if saw_unresolved else False


def _observed_atomic_for_vid(vid: str, field_map: dict[str, str]) -> str | None:
    field_order = _field_order_for_vid(vid)
    if not field_order:
        values = sorted(field_map.items())
        return ";".join(f"{key}={value}" for key, value in values) if values else None
    parts = []
    for field in field_order:
        if field in field_map:
            parts.append(f"{field}={field_map[field]}")
    if not parts and field_map:
        parts = [f"{key}={value}" for key, value in sorted(field_map.items())]
    if len(parts) == 1:
        return parts[0].split("=", 1)[1]
    return ";".join(parts) if parts else None


def rust_live_row(
    vid: str,
    field_map: dict[str, str],
    *,
    evidence_source: str,
) -> dict[str, Any]:
    binding = factory_binding_for_vid(vid)
    if not binding:
        raise RuntimeError(f"missing factory binding for {vid}")
    pass_predicate, fail_predicate = _predicate_texts(binding)
    if not pass_predicate or not fail_predicate:
        raise RuntimeError(f"binding for {vid} is missing pass/fail predicates")
    fail_result = _evaluate_predicate(field_map, binding, fail_predicate)
    pass_result = _evaluate_predicate(field_map, binding, pass_predicate)

    unresolved_reason = None
    if fail_result is True:
        verdict = "fail"
        partition_class = "noncompliant"
    elif pass_result is True and fail_result is not True:
        verdict = "pass"
        partition_class = "compliant"
    else:
        verdict = "unresolved"
        partition_class = "indeterminate"
        unresolved_reason = "predicate could not be resolved from available normalized evidence"

    return {
        "measurableId": vid,
        "requiredAtomic": _required_atomic_for_vid(vid),
        "observedAtomic": _observed_atomic_for_vid(vid, field_map),
        "operator": _operator_for_vid(vid),
        "verdict": verdict,
        "evidenceSource": evidence_source,
        "comparisonExpression": _operator_for_vid(vid),
        "partitionClass": partition_class,
        "unresolvedReason": unresolved_reason,
    }


def projected_unresolved_row(
    control: dict[str, Any],
    *,
    detail: str,
) -> list[dict[str, Any]]:
    vid = str(control.get("vuln_id") or "")
    bundle = load_factory_bundle()
    binding = bundle.get("_bindingsByVid", {}).get(vid, {})
    sources = control.get("tmsh_commands") or control.get("rest_endpoints") or []
    return [
        {
            "measurableId": vid or "control_adapter",
            "requiredAtomic": binding.get(
                "required_atomic_description",
                "canonical adapter fixture",
            ),
            "observedAtomic": None,
            "operator": "projected_unresolved",
            "verdict": "unresolved",
            "evidenceSource": ",".join(sources) if sources else "none",
            "comparisonExpression": detail,
            "partitionClass": "indeterminate",
        }
    ]


def evaluate(control: dict[str, Any], evidence: dict[str, str]) -> list[dict[str, Any]]:
    vid = control.get("vuln_id") or ""
    if vid in {"V-266084", "V-266150"}:
        return evaluate_virtual_services(control, evidence)
    if vid == "V-266095":
        return evaluate_v266095(evidence)
    if vid == "V-266170":
        return evaluate_v266170(control, evidence)
    recipe = recipe_for_vid(vid)
    if not recipe:
        return projected_unresolved_row(
            control,
            detail="no Rust-emitted capture recipe available for this control",
        )
    if not evidence:
        return projected_unresolved_row(
            control,
            detail="capture recipe available, but no live evidence has been collected yet",
        )
    normalized = normalize_with_recipe(control, evidence)
    try:
        return [
            rust_live_row(
                vid,
                normalized.get("fieldMap") or {},
                evidence_source="recipe::" + ",".join(sorted(evidence.keys())),
            )
        ]
    except Exception as exc:  # noqa: BLE001
        return projected_unresolved_row(
            control,
            detail=f"Rust live evaluation unavailable: {exc}",
        )


def synthetic_good_evidence(control: dict[str, Any]) -> dict[str, str]:
    """Known-good fixture: all measurables should pass."""
    vid = control["vuln_id"]
    if vid in {"V-266084", "V-266150"}:
        return {"tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n destination /Common/192.0.2.10:https\n enabled\n ip-protocol tcp\n}\n"}
    if vid == "V-266095":
        return {
            "tmsh list sys httpd all-properties": "sys httpd { auth-pam-idle-timeout 300 auth-pam-dashboard-timeout on }\n",
            "tmsh list cli global-settings all-properties": "cli global-settings { idle-timeout 5 }\n",
            "tmsh list sys global-settings all-properties": "sys global-settings { console-inactivity-timeout 300 }\n",
            "/mgmt/tm/sys/sshd": json.dumps({"inactivityTimeout": 300}),
        }
    if vid == "V-266170":
        return {
            "tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n enabled\n profiles {\n  clientssl { context clientside }\n }\n}\n",
            "tmsh list ltm profile client-ssl all-properties": "ltm profile client-ssl clientssl {\n ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384\n partition Common\n}\n",
        }
    return {}


def synthetic_bad_evidence(control: dict[str, Any]) -> dict[str, str]:
    """Known-bad fixture: at least one measurable should fail."""
    vid = control["vuln_id"]
    if vid in {"V-266084", "V-266150"}:
        return {"tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n destination /Common/192.0.2.10:any\n enabled\n ip-protocol tcp\n}\n"}
    if vid == "V-266095":
        return {
            "tmsh list sys httpd all-properties": "sys httpd { auth-pam-idle-timeout 300 auth-pam-dashboard-timeout on }\n",
            "tmsh list cli global-settings all-properties": "cli global-settings { idle-timeout 5 }\n",
            "tmsh list sys global-settings all-properties": "sys global-settings { console-inactivity-timeout 0 }\n",
            "/mgmt/tm/sys/sshd": json.dumps({"inactivityTimeout": 300}),
        }
    if vid == "V-266170":
        return {
            "tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n enabled\n profiles {\n  clientssl { context clientside }\n }\n}\n",
            "tmsh list ltm profile client-ssl all-properties": "ltm profile client-ssl clientssl {\n ciphers ALL:!DH:!ADH:!EDH:@SPEED\n partition Common\n}\n",
        }
    return {}


def synthetic_disabled_evidence(control: dict[str, Any]) -> dict[str, str]:
    """Evidence where the feature is explicitly disabled / set to none."""
    vid = control["vuln_id"]
    if vid in {"V-266084", "V-266150"}:
        return {"tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n destination /Common/192.0.2.10:https\n disabled\n ip-protocol tcp\n}\n"}
    if vid == "V-266095":
        return {
            "tmsh list sys httpd all-properties": "sys httpd { auth-pam-idle-timeout disabled auth-pam-dashboard-timeout off }\n",
            "tmsh list cli global-settings all-properties": "cli global-settings { idle-timeout disabled }\n",
            "tmsh list sys global-settings all-properties": "sys global-settings { console-inactivity-timeout 0 }\n",
            "/mgmt/tm/sys/sshd": json.dumps({"inactivityTimeout": 0}),
        }
    if vid == "V-266170":
        return {
            "tmsh list ltm virtual all-properties": "ltm virtual /Common/dp_vs {\n disabled\n profiles {\n  clientssl { context clientside }\n }\n}\n",
            "tmsh list ltm profile client-ssl all-properties": "ltm profile client-ssl clientssl {\n ciphers none\n partition Common\n}\n",
        }
    return {}


def synthetic_absent_evidence(control: dict[str, Any]) -> dict[str, str]:
    """No evidence at all -- equivalent to RawEvidence::Missing."""
    return {}


def synthetic_malformed_evidence(control: dict[str, Any]) -> dict[str, str]:
    """Garbage / corrupt payload for every expected evidence source."""
    vid = control["vuln_id"]
    garbage = "<<<CORRUPT_PAYLOAD::0xDEADBEEF>>>"
    if vid in {"V-266084", "V-266150"}:
        return {"tmsh list ltm virtual all-properties": garbage}
    if vid == "V-266095":
        return {
            "tmsh list sys httpd all-properties": garbage,
            "tmsh list cli global-settings all-properties": garbage,
            "tmsh list sys global-settings all-properties": garbage,
            "/mgmt/tm/sys/sshd": garbage,
        }
    if vid == "V-266170":
        return {
            "tmsh list ltm virtual all-properties": garbage,
            "tmm list ltm profile client-ssl all-properties": garbage,
        }
    return {}


def validation_bundle(host: str, vid: str, client: F5Client | None = None) -> dict[str, Any]:
    catalog = load_catalog()
    control = catalog[vid]
    evidence = capture_for_control(client, control) if client else {}
    rows = evaluate(control, evidence)
    status = status_from_rows(rows)
    validation_hash = stable_hash({"host": host, "vid": vid, "rows": rows, "status": status})
    bundle = {
        "kind": "ValidationViewBundle",
        "bundleId": f"validation:{host}:{vid}:{validation_hash[:12]}",
        "hostId": host,
        "vid": vid,
        "status": status,
        "provenancePanel": {
            "gateStatus": "advisory_only",
            "trustRoot": "export-local",
            "witnessRef": control.get("assertion_id", ""),
            "pullbackRef": validation_hash,
            "evidenceRefs": sorted(evidence.keys()),
            "scope": {"hostId": host, "vid": vid},
            "note": "Rendered by UI from backend-produced atomic comparison rows.",
        },
        "evidenceTable": rows,
        "pullbackSummary": {
            "text": f"{sum(1 for item in rows if item['verdict'] == 'pass')}/{len(rows)} atomic pullback row(s) pass.",
            "criticismNote": "Browser renders only this bundle; it does not recompute judgment.",
        },
        "rawEvidenceLinks": [
            {"source": key, "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(), "preview": value[:240]}
            for key, value in sorted(evidence.items())
        ],
        "partitionSummary": partition_summary(rows),
        "falsifierRefs": control.get("evidence_required", []),
        "criticismRefs": [],
        "provenance": {
            "validationRecordHash": validation_hash,
            "pullbackRecordHash": validation_hash,
        },
    }
    return bundle


def adjudication_bundle(validation: dict[str, Any]) -> dict[str, Any]:
    rows = validation.get("evidenceTable", [])
    counts = {
        "pass": sum(1 for item in rows if item.get("verdict") == "pass"),
        "fail": sum(1 for item in rows if item.get("verdict") == "fail"),
        "unresolved": sum(1 for item in rows if item.get("verdict") == "unresolved"),
    }
    status = validation.get("status", "unresolved")
    digest = stable_hash({"validation": validation.get("bundleId"), "counts": counts, "status": status})
    return {
        "kind": "AdjudicationViewBundle",
        "bundleId": f"adjudication:{digest[:12]}",
        "hostId": validation["hostId"],
        "vid": validation["vid"],
        "status": status,
        "rationale": validation["pullbackSummary"]["text"],
        "criteriaDetail": "Backend adjudication over atomic pullback rows only.",
        "counts": counts,
        "proofChain": [
            {"phase": "observe", "title": "Evidence captured", "detail": f"{len(validation.get('rawEvidenceLinks', []))} source(s)", "verdict": "pass"},
            {"phase": "pullback", "title": "Atomic pullback rows", "detail": f"{len(rows)} comparison row(s)", "verdict": "pass" if counts["fail"] == 0 and counts["unresolved"] == 0 else "fail"},
            {"phase": "criteria", "title": "Bundle status", "detail": status, "verdict": "pass" if status == "not_a_finding" else "fail"},
        ],
        "matchedPairs": rows,
        "validationIssues": [],
        "falsifierRefs": validation.get("falsifierRefs", []),
        "criticismRefs": validation.get("criticismRefs", []),
        "provenance": {
            "adjudicationRecordHash": digest,
            "validationBundleId": validation["bundleId"],
        },
    }

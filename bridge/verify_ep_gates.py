import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPORT_BUNDLE_PATH = ROOT / "bridge" / "ExportBundle.json"
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"
EXPORT_HTML_PATH = ROOT / "export" / "stig_expert_critic.html"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_js_blocks(html_text):
    pattern = re.compile(
        r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>",
        re.DOTALL | re.IGNORECASE,
    )
    blocks = []
    for match in pattern.finditer(html_text):
        attrs = match.group("attrs") or ""
        if 'type="application/json"' in attrs or "type='application/json'" in attrs:
            continue
        blocks.append(match.group("body"))
    return blocks


def load_inputs():
    export_bundle = load_json(EXPORT_BUNDLE_PATH)
    projection_bundle = load_json(PROJECTION_BUNDLE_PATH)
    html_text = EXPORT_HTML_PATH.read_text(encoding="utf-8")
    js_text = "\n".join(extract_js_blocks(html_text))
    return export_bundle, projection_bundle, html_text, js_text


def gate_ep1(js_text):
    if "> " in js_text or "< " in js_text:
        return False, "comparison token found in JS"
    return True, "no independent judgment tokens found"


def gate_ep2(js_text):
    for token in [" AND ", " OR ", "parse_criteria"]:
        if token in js_text:
            return False, f"DSL token found: {token}"
    return True, "no DSL tokens found"


def gate_ep3(export_bundle, projection_bundle):
    projection_by_vid = {item["vuln_id"]: item for item in projection_bundle}
    unresolved_total = 0
    unresolved_ok = 0
    for entry in export_bundle["entries"]:
        if entry["status"] == "projected_unresolved":
            unresolved_total += 1
            if projection_by_vid[entry["vuln_id"]]["stig_verdict"] != "not_a_finding":
                unresolved_ok += 1
    if unresolved_ok != unresolved_total:
        return False, f"unresolved preserved {unresolved_ok}/{unresolved_total}"
    return True, f"unresolved preserved {unresolved_ok}/{unresolved_total}"


def gate_ep4(export_bundle, projection_bundle):
    export_by_vid = {item["vuln_id"]: item for item in export_bundle["entries"]}
    for item in projection_bundle:
        if item["display_status"] == "live_resolved":
            source = export_by_vid[item["vuln_id"]]
            if source["status"] != "resolved" or source["legitimacy"] != "9/9":
                return False, f"promotion mismatch for {item['vuln_id']}"
    return True, "resolution appears only for promoted controls"


def gate_ep5(export_bundle, projection_bundle):
    matches = 0
    total = len(projection_bundle)
    projection_by_vid = {item["vuln_id"]: item for item in projection_bundle}
    for entry in export_bundle["entries"]:
        projected = projection_by_vid[entry["vuln_id"]]
        expected = entry["verdict"]
        if (
            entry["status"] == "projected_unresolved"
            and any("was: fail" in item for item in entry.get("provenance_chain", []))
        ):
            expected = "open"
        if projected["stig_verdict"] == expected:
            matches += 1
    if matches != total:
        return False, f"projection equivalence {matches}/{total}"
    return True, f"projection equivalence {matches}/{total}"


def gate_ep6(export_bundle, projection_bundle, html_text):
    if '<script type="application/json" id="projection-data">' not in html_text:
        return False, "projection data block missing"
    counts = {}
    for item in projection_bundle:
        counts[item["display_status"]] = counts.get(item["display_status"], 0) + 1
    promoted = counts.get("live_resolved", 0)
    unresolved = (
        counts.get("blocked_external", 0)
        + counts.get("open_finding", 0)
        + counts.get("pending_promotion", 0)
    )
    summary = export_bundle["summary"]
    if promoted != summary["promoted"] or unresolved != summary["projected_unresolved"]:
        return False, "summary counts do not match"
    return True, "scope count consistency holds"


def gate_ep7(projection_bundle):
    for item in projection_bundle:
        if not isinstance(item["provenance"], list) or len(item["provenance"]) == 0:
            return False, f"missing provenance for {item['vuln_id']}"
        if item["display_status"] == "live_resolved" and len(item["provenance"]) < 3:
            return False, f"resolved item missing provenance depth for {item['vuln_id']}"
    return True, "provenance preserved"


def gate_ep8(js_text):
    if "live_validate_enabled === true" not in js_text:
        return False, "validate button not explicitly gated"
    return True, "validate button gated on packaged projection field"


def gate_ep9(js_text):
    pattern = re.compile(r"\b(?:let|const|var)\s+(?:verdict|pass|fail)\b")
    if pattern.search(js_text):
        return False, "forbidden local semantic variable found"
    return True, "no local verdict variables found"


def gate_ep10(js_text):
    pattern = re.compile(r"function\s+(?:evaluate|promote|witness|assess|judge)\b")
    match = pattern.search(js_text)
    if match:
        return False, f"forbidden function found: {match.group(0)}"
    return True, "no evaluation functions found"


def gate_ep11(projection_bundle):
    for item in projection_bundle:
        if item["display_status"] != "live_resolved":
            if not item["explanation"]:
                return False, f"missing explanation for {item['vuln_id']}"
            if not item["legitimacy"]:
                return False, f"missing legitimacy for {item['vuln_id']}"
            if item["live_validate_enabled"] is not False:
                return False, f"live validate enabled on unresolved item {item['vuln_id']}"
    return True, "projected unresolved semantics preserved"


def gate_ep12(js_text):
    required_bits = [
        'data-vid',
        'currentVid = holder.getAttribute("data-vid")',
        "drawDetail()",
        'entry.vuln_id === currentVid',
    ]
    for token in required_bits:
        if token not in js_text:
            return False, f"state isolation token missing: {token}"
    return True, "state isolation logic present"


def run_checks():
    export_bundle, projection_bundle, html_text, js_text = load_inputs()
    projection_by_vid = {item["vuln_id"]: item for item in projection_bundle}
    gates = [
        ("EP-1", gate_ep1(js_text)),
        ("EP-2", gate_ep2(js_text)),
        ("EP-3", gate_ep3(export_bundle, projection_bundle)),
        ("EP-4", gate_ep4(export_bundle, projection_bundle)),
        ("EP-5", gate_ep5(export_bundle, projection_bundle)),
        ("EP-6", gate_ep6(export_bundle, projection_bundle, html_text)),
        ("EP-7", gate_ep7(projection_bundle)),
        ("EP-8", gate_ep8(js_text)),
        ("EP-9", gate_ep9(js_text)),
        ("EP-10", gate_ep10(js_text)),
        ("EP-11", gate_ep11(projection_bundle)),
        ("EP-12", gate_ep12(js_text)),
    ]
    passed = sum(1 for _, result in gates if result[0])
    unresolved_total = sum(
        1 for item in export_bundle["entries"] if item["status"] == "projected_unresolved"
    )
    unresolved_ok = sum(
        1
        for item in export_bundle["entries"]
        if item["status"] == "projected_unresolved"
        and projection_by_vid[item["vuln_id"]]["stig_verdict"] != "not_a_finding"
    )
    projection_matches = sum(
        1
        for item in export_bundle["entries"]
        if projection_by_vid[item["vuln_id"]]["stig_verdict"]
        == (
            "open"
            if (
                item["status"] == "projected_unresolved"
                and any("was: fail" in line for line in item.get("provenance_chain", []))
            )
            else item["verdict"]
        )
    )
    role_drift = 0 if gates[9][1][0] else 1
    truth_invention = (0 if gates[0][1][0] else 1) + (0 if gates[1][1][0] else 1)
    return {
        "gates": gates,
        "passed": passed,
        "projection_equivalence_rate": projection_matches / len(projection_bundle),
        "unresolved_preservation_rate": unresolved_ok / unresolved_total,
        "scope_fidelity_rate": len(projection_bundle) / export_bundle["summary"]["total"],
        "role_drift_incidents": role_drift,
        "frontend_truth_invention_incidents": truth_invention,
    }


def main():
    summary = run_checks()
    for gate_id, result in summary["gates"]:
        ok, detail = result
        if ok:
            print(f"{gate_id}: PASS")
        else:
            print(f"{gate_id}: FAIL - {detail}")
    if summary["passed"] == 12:
        print("EP GATE: PASS (12/12 gates passed)")
    else:
        print(f"EP GATE: FAIL ({summary['passed']}/12 gates passed)")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

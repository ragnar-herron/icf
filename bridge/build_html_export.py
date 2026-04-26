import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"
TEMPLATE_PATH = ROOT / "docs" / "expert_critic_template.html"
EXPORT_DIR = ROOT / "export"
EXPORT_HTML_PATH = EXPORT_DIR / "stig_expert_critic.html"

FORBIDDEN_JS_TOKENS = [
    "eval(",
    " AND ",
    " OR ",
    "function evaluate",
    "function assess",
    "function judge",
    "function promote",
    "function witness",
]


def load_projection_bundle(path: Path = PROJECTION_BUNDLE_PATH):
    if not path.exists():
        raise FileNotFoundError(f"missing projection bundle: {path}")
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


def template_without_scripts():
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    text = re.sub(r"<script[^>]*>.*?</script>\s*</body>", "</body>", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("<title>STIG CPE â€“ F5 BIG-IP</title>", "<title>STIG Expert Critic</title>")
    text = text.replace("<h1>STIG CPE</h1>", "<h1>STIG Expert Critic</h1>")
    text = text.replace('>F5 BIG-IP</span>', '>ICF Compliance Report</span>')
    text = text.replace("gate: checkingâ€¦", "projection: certified")
    return text


def projection_script():
    return """<script>
var bundleData = JSON.parse(document.getElementById("projection-data").textContent);
var filterState = "";
var currentVid = bundleData.length !== 0 ? bundleData[0].vuln_id : null;

function element(id) {
  return document.getElementById(id);
}

function show(id) {
  element(id).classList.remove("hidden");
}

function hide(id) {
  element(id).classList.add("hidden");
}

function setText(id, value) {
  element(id).textContent = value;
}

function setHtml(id, value) {
  element(id).innerHTML = value;
}

function escHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function statusBadge(item) {
  if (item.display_status === "blocked_external") {
    return '<span class="badge-status st-unknown">BLOCKED</span>';
  }
  if (item.display_status === "pending_promotion") {
    return '<span class="badge-status st-error">PENDING</span>';
  }
  if (item.display_status === "open_finding" || item.stig_verdict === "open") {
    return '<span class="badge-status st-open">OPEN</span>';
  }
  return '<span class="badge-status st-not_a_finding">NOT A FINDING</span>';
}

function iconInfo(item) {
  if (item.display_status === "blocked_external") {
    return { marker: "!", css: "vid-unknown" };
  }
  if (item.display_status === "pending_promotion") {
    return { marker: ".", css: "vid-unknown" };
  }
  if (item.display_status === "open_finding" || item.stig_verdict === "open") {
    return { marker: "X", css: "vid-fail" };
  }
  return { marker: "+", css: "vid-pass" };
}

function severityClass(value) {
  if (value === "high") {
    return "sev-high";
  }
  if (value === "medium") {
    return "sev-medium";
  }
  return "sev-low";
}

function liveCounts() {
  return bundleData.reduce(function(acc, item) {
    acc[item.display_status] = (acc[item.display_status] || 0) + 1;
    return acc;
  }, {});
}

function selectedItem() {
  return bundleData.find(function(entry) {
    return entry.vuln_id === currentVid;
  }) || null;
}

function advisoryOnlyMessage() {
  return "This packaged export is a certified projection surface. Live execution is not available in the standalone wrapper.";
}

function doConnect() {
  window.alert(advisoryOnlyMessage());
}

function doDisconnect() {
  window.alert(advisoryOnlyMessage());
}

function doValidate() {
  var item = selectedItem();
  if (item === null) {
    window.alert("Select a STIG control first.");
    return;
  }
  renderValidate(item);
  renderAdjudication(item);
  renderLocalRepair(item);
  switchTab("tab-validate");
  if (item.live_validate_enabled === true) {
    window.alert("This packaged export preserves the certified live result for this control. No new live collection occurs in the standalone wrapper.");
  } else {
    window.alert(advisoryOnlyMessage());
  }
}

function doValidateAll() {
  window.alert("Validate All is not available in the packaged wrapper. Use the certified projected statuses already shown in the sidebar.");
}

function doRecommendedTmshRemediation() {
  window.alert(advisoryOnlyMessage());
}

function doRecommendedRestRemediation() {
  window.alert(advisoryOnlyMessage());
}

function captureLocalResiduals() {
  window.alert(advisoryOnlyMessage());
}

function doLocalRepairTmsh() {
  window.alert(advisoryOnlyMessage());
}

function doTmshQuery() {
  var item = selectedItem();
  if (item === null) {
    window.alert("Select a STIG control first.");
    return;
  }
  setText("tmsh-q-result", advisoryOnlyMessage());
  show("tmsh-q-result");
}

function doRestQuery() {
  var item = selectedItem();
  if (item === null) {
    window.alert("Select a STIG control first.");
    return;
  }
  setText("rest-q-result", advisoryOnlyMessage());
  show("rest-q-result");
}

function doVerify() {
  setText("verify-status", "Packaged export only: verify is not available in this wrapper.");
  element("verify-status").className = "status-msg fail";
  show("verify-status");
}

function doMerge() {
  window.alert(advisoryOnlyMessage());
}

function doSaveConfig() {
  window.alert(advisoryOnlyMessage());
}

function doLoadSnippet() {
  var item = selectedItem();
  if (item === null) {
    window.alert("Select a STIG control first.");
    return;
  }
  var snippet = "";
  if (item.remediation && item.remediation.tmsh_equivalent) {
    snippet = item.remediation.tmsh_equivalent;
  } else if (item.remediation && item.remediation.commands) {
    snippet = item.remediation.commands.join("\\n");
  } else {
    snippet = "# No packaged snippet for this control";
  }
  element("merge-editor").value = snippet;
}

function doSaveSnippet() {
  window.alert(advisoryOnlyMessage());
}

function showGateDetail() {
  var counts = liveCounts();
  window.alert(
    "Certified projection bundle\\n\\n"
    + "live_resolved: " + (counts.live_resolved || 0) + "\\n"
    + "blocked_external: " + (counts.blocked_external || 0) + "\\n"
    + "open_finding: " + (counts.open_finding || 0) + "\\n"
    + "pending_promotion: " + (counts.pending_promotion || 0)
  );
}

function toggleFiberTable() {
  var body = element("adj-fiber-body");
  var toggle = element("adj-fiber-toggle");
  var hiddenNow = body.style.display === "none" || body.style.display === "";
  body.style.display = hiddenNow ? "block" : "none";
  toggle.innerHTML = hiddenNow ? "&#9650;" : "&#9660;";
}

function switchTab(tabId) {
  Array.prototype.forEach.call(document.querySelectorAll(".tab-btn"), function(btn) {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });
  Array.prototype.forEach.call(document.querySelectorAll(".tab-panel"), function(panel) {
    panel.classList.toggle("active", panel.id === tabId);
  });
}

function filterItems() {
  var query = element("stig-filter").value.toLowerCase();
  var severity = element("severity-filter").value;
  return bundleData.filter(function(item) {
    var textOk = item.vuln_id.toLowerCase().includes(query) || String(item.title || "").toLowerCase().includes(query);
    var severityOk = severity === "" || item.severity === severity;
    return textOk && severityOk;
  });
}

function renderSidebar() {
  var list = element("stig-list");
  var items = filterItems();
  if (items.length === 0) {
    list.innerHTML = '<div class="placeholder" style="padding:16px 0">No controls match the current filter.</div>';
    return;
  }
  if (items.every(function(item) { return item.vuln_id !== currentVid; })) {
    currentVid = items[0].vuln_id;
  }
  list.innerHTML = items.map(function(item) {
    var icon = iconInfo(item);
    var selected = item.vuln_id === currentVid ? " selected" : "";
    return ''
      + '<div class="stig-item' + selected + '" data-vid="' + item.vuln_id + '">'
      + '<span class="vid ' + icon.css + '">' + item.vuln_id + '</span>'
      + '<span class="sev ' + severityClass(item.severity) + '">' + icon.marker + ' ' + item.severity + '</span>'
      + '</div>';
  }).join("");
}

function renderBanner(item) {
  show("contract-banner");
  setText("banner-vid", item.vuln_id);
  setText("banner-title", String(item.title || ""));
  setHtml("banner-status", statusBadge(item));
  setText("tab-vid-indicator", item.vuln_id);
  element("tab-vid-indicator").classList.add("active");
  setText("validate-vid-pin", item.vuln_id);
  setText("tmsh-q-vid-pin", item.vuln_id);
  setText("rest-q-vid-pin", item.vuln_id);
  setText("local-repair-vid-pin", item.vuln_id);
  setText("merge-vid-banner", "Pinned control: " + item.vuln_id);
}

function renderContract(item) {
  hide("no-sel-msg");
  show("contract-detail");
  setText("d-vid", item.vuln_id);
  setHtml("d-sev", '<span class="sev ' + severityClass(item.severity) + '">' + String(item.severity || "").toUpperCase() + '</span>');
  setText("d-title", String(item.title || ""));
  if (item.remediation && item.remediation.method) {
    setText("d-method", item.remediation.method);
  } else {
    setText("d-method", "No packaged remediation metadata");
  }
  if (item.pullback_row && item.pullback_row.fields) {
    setText("d-evidence", item.pullback_row.fields.join(", "));
  } else {
    setText("d-evidence", "No live evidence summary packaged for this control.");
  }
  setText("d-criteria", JSON.stringify({
    display_status: item.display_status,
    stig_verdict: item.stig_verdict,
    live_validate_enabled: item.live_validate_enabled
  }, null, 2));
  if (item.remediation && item.remediation.tmsh_equivalent) {
    setText("d-tmsh", item.remediation.tmsh_equivalent);
  } else if (item.remediation && item.remediation.commands) {
    setText("d-tmsh", item.remediation.commands.join("\\n"));
  } else {
    setText("d-tmsh", "No TMSH command packaged.");
  }
  if (item.remediation && item.remediation.endpoint) {
    setText("d-rest", item.remediation.endpoint);
  } else {
    setText("d-rest", "No REST endpoint packaged.");
  }
  hide("d-org-policy-section");
}

function evidenceTable(item) {
  if (item.evidence_summary === null) {
    return '<div class="placeholder" style="padding:16px 0">No resolved live evidence is packaged for this control.</div>';
  }
  var rows = Object.keys(item.evidence_summary).map(function(key) {
    return '<tr><th>' + key + '</th><td>' + JSON.stringify(item.evidence_summary[key]) + '</td></tr>';
  }).join("");
  return '<table class="ev-table"><thead><tr><th>Field</th><th>Observed</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

function pullbackTable(item) {
  if (item.pullback_row === null) {
    return '<div class="placeholder" style="padding:16px 0">' + String(item.explanation || "No pullback row packaged.") + '</div>';
  }
  var rows = item.pullback_row.fields.map(function(name) {
    return '<tr><td>' + name + '</td><td>' + JSON.stringify(item.pullback_row.required[name]) + '</td><td>' + JSON.stringify(item.pullback_row.observed[name]) + '</td></tr>';
  }).join("");
  return '<table class="ev-table"><thead><tr><th>Field</th><th>Required</th><th>Observed</th></tr></thead><tbody>' + rows + '</tbody></table>';
}

function rowStatusInfo(item) {
  if (item.pullback_row === null) {
    return { label: "unresolved", css: "card-unresolved", row: "row-unresolved" };
  }
  if (item.pullback_row.verdict === "pass") {
    return { label: "ok", css: "card-ok", row: "row-pass" };
  }
  if (item.pullback_row.verdict === "fail") {
    return { label: "mismatch", css: "card-mismatch", row: "row-fail" };
  }
  return { label: "unresolved", css: "card-unresolved", row: "row-unresolved" };
}

function fiberDetailTable(item) {
  if (item.pullback_row === null || !item.pullback_row.fields || item.pullback_row.fields.length === 0) {
    return '<div class="placeholder" style="padding:16px 0">' + escHtml(item.explanation || "No promoted adapter fiber row is packaged for this control.") + '</div>';
  }
  var status = rowStatusInfo(item);
  var required = item.pullback_row.required || {};
  var observed = item.pullback_row.observed || {};
  var rows = item.pullback_row.fields.map(function(name, index) {
    var comparisonId = item.vuln_id + "::" + (index + 1);
    var expression = name + " " + String(required[name] == null ? "" : required[name]);
    return ''
      + '<tr class="' + status.row + '">'
      + '<td>' + escHtml(comparisonId) + '</td>'
      + '<td>' + escHtml(name) + '</td>'
      + '<td>' + escHtml(JSON.stringify(observed[name])) + '</td>'
      + '<td>' + escHtml(JSON.stringify(required[name])) + '</td>'
      + '<td>' + escHtml(expression) + '</td>'
      + '<td>' + escHtml(item.evidence_ref || "live_state/full_campaign") + '</td>'
      + '<td class="' + status.css + '">' + escHtml(status.label) + '</td>'
      + '</tr>';
  }).join("");
  return ''
    + '<table class="fiber-table">'
    + '<thead><tr><th>Comparison ID</th><th>Measurable</th><th>Observed Value</th><th>Required Value</th><th>Expression</th><th>Evidence Source</th><th>Match Status</th></tr></thead>'
    + '<tbody>' + rows + '</tbody>'
    + '</table>';
}

function renderValidate(item) {
  setHtml("val-status", statusBadge(item));
  show("val-provenance");
  setHtml("val-provenance", ''
    + '<h4>Raw Evidence Provenance</h4>'
    + '<div class="provenance-grid">'
    + '<div class="provenance-item"><span class="label">Display Status</span><span class="value">' + item.display_status + '</span></div>'
    + '<div class="provenance-item"><span class="label">Legitimacy</span><span class="value">' + item.legitimacy + '</span></div>'
    + '<div class="provenance-item"><span class="label">DP Gates</span><span class="value">' + item.dp_gates + '</span></div>'
    + '</div>'
    + '<div class="provenance-note">' + (item.explanation || "Certified live result preserved from the bridge output.") + '</div>'
  );
  setHtml("val-evidence", evidenceTable(item));
  show("res-content");
  hide("res-empty");
  setHtml("res-pullback-summary", '<div class="pullback-summary"><span class="pb-label">STIG Specification</span><div>' + (item.explanation || "Packaged live-aligned pullback row.") + '</div></div>');
  setHtml("res-comparison-summary", item.pullback_row === null ? "Packaged explanation only" : "Required vs observed values");
  setHtml("res-comparison-all", pullbackTable(item));
  hide("res-unmatched-card");
  hide("val-log");
  element("btn-validate").disabled = item.live_validate_enabled !== true;
}

function outcomeClass(item) {
  if (item.display_status === "blocked_external" || item.display_status === "pending_promotion") {
    return "outcome-unknown";
  }
  if (item.display_status === "open_finding" || item.stig_verdict === "open") {
    return "outcome-fail";
  }
  return "outcome-pass";
}

function renderAdjudication(item) {
  hide("adj-empty");
  show("adj-content");
  element("adj-outcome-banner").className = "adj-outcome-banner " + outcomeClass(item);
  setText("adj-badge", item.display_status === "live_resolved" ? item.stig_verdict.replaceAll("_", " ").toUpperCase() : item.display_status.replaceAll("_", " ").toUpperCase());
  setText("adj-vid-label", item.vuln_id);
  setText("adj-req-label", item.pullback_row ? item.pullback_row.operator_summary : "Certified projected status");
  setHtml("adj-evidence-counts", item.pullback_row ? '<span class="ec-pass">measurables: ' + item.pullback_row.fields.length + '</span>' : '<span class="ec-unresolved">projection only</span>');
  setText("adj-why", item.explanation || "The certified export preserves the live-resolved determination for this control.");
  setText("adj-criteria-detail", JSON.stringify({ display_status: item.display_status, live_validate_enabled: item.live_validate_enabled }, null, 2));
  if (item.pullback_row) {
    show("adj-fiber-card");
    setText("adj-fiber-count", "(" + item.pullback_row.fields.length + " matched pair" + (item.pullback_row.fields.length === 1 ? "" : "s") + ")");
    setHtml("adj-fiber-table", fiberDetailTable(item));
    element("adj-fiber-body").style.display = "block";
    element("adj-fiber-toggle").innerHTML = "&#9650;";
  } else {
    hide("adj-fiber-card");
  }
  setHtml("adj-proof-summary", item.pullback_row ? "projection to pullback to packaged determination" : "projection to packaged explanation");
  setHtml("adj-proof-chain", ''
    + '<div class="proof-step"><div class="ps-icon ic-observe">1</div><div class="ps-body"><div class="ps-title">Observe</div><div class="ps-detail">' + (item.pullback_row ? "Observed evidence was preserved into the export bundle." : "No resolved live evidence was packaged for this control.") + '</div></div></div>'
    + '<div class="proof-step"><div class="ps-icon ic-pullback">2</div><div class="ps-body"><div class="ps-title">Project</div><div class="ps-detail">The standalone wrapper renders only the certified projection bundle.</div></div></div>'
    + '<div class="proof-step"><div class="ps-icon ic-criteria">3</div><div class="ps-body"><div class="ps-title">Determine</div><div class="ps-detail">' + (item.explanation || "The packaged result remains live-resolved and certified.") + '</div></div></div>'
  );
  hide("adj-viol-section");
}

function remediationText(item) {
  if (!item.remediation) {
    return "No packaged remediation metadata is available for this control.";
  }
  if (item.remediation.note) {
    return item.remediation.note;
  }
  return "Use the packaged remediation object below as advisory guidance.";
}

function renderRemediation(item) {
  hide("remediate-vuln-specific");
  setText("remediate-precision-summary", remediationText(item));
  show("remediate-note-card");
  setText("remediate-note", remediationText(item));
  setText("remediate-method-label", item.remediation && item.remediation.method ? item.remediation.method : "No method packaged");
  if (item.remediation && item.remediation.tmsh_equivalent) {
    element("remediate-tmsh-command").value = item.remediation.tmsh_equivalent;
  } else if (item.remediation && item.remediation.commands) {
    element("remediate-tmsh-command").value = item.remediation.commands.join("\\n");
  } else {
    element("remediate-tmsh-command").value = "";
  }
  if (item.remediation && item.remediation.endpoint) {
    element("remediate-rest-command").value = JSON.stringify({
      endpoint: item.remediation.endpoint,
      payload: item.remediation.payload || null
    }, null, 2);
  } else {
    element("remediate-rest-command").value = "";
  }
  setText("remediate-tmsh-precision", advisoryOnlyMessage());
  setText("remediate-rest-precision", advisoryOnlyMessage());
  element("btn-remediate-tmsh").disabled = true;
  element("btn-remediate-rest").disabled = true;
  hide("remediate-tmsh-status");
  hide("remediate-rest-status");
  hide("remediate-tmsh-console");
  hide("remediate-rest-console");
}

function renderLocalRepair(item) {
  if (item.pullback_row === null) {
    hide("local-repair-content");
    show("local-repair-empty");
    return;
  }
  hide("local-repair-empty");
  show("local-repair-content");
  setText("local-repair-summary", "The packaged export preserves the current measurable rows for local review only.");
  setHtml("local-repair-table", pullbackTable(item));
  if (item.remediation && item.remediation.tmsh_equivalent) {
    element("local-repair-command").value = item.remediation.tmsh_equivalent;
  } else {
    element("local-repair-command").value = "";
  }
  element("btn-capture-residuals").disabled = true;
  element("btn-local-repair-tmsh").disabled = true;
}

function renderQueryHints(item) {
  if (item.remediation && item.remediation.tmsh_equivalent) {
    setText("tmsh-q-hint", item.remediation.tmsh_equivalent);
    show("tmsh-q-hint");
  } else {
    hide("tmsh-q-hint");
  }
  if (item.remediation && item.remediation.endpoint) {
    setText("rest-q-hint", item.remediation.endpoint);
    show("rest-q-hint");
  } else {
    hide("rest-q-hint");
  }
}

function renderMerge(item) {
  if (item.remediation && item.remediation.tmsh_equivalent) {
    element("merge-editor").value = item.remediation.tmsh_equivalent;
  } else {
    element("merge-editor").value = "";
  }
  element("btn-save-snippet").disabled = true;
  element("btn-merge").disabled = true;
  element("btn-save").disabled = true;
  setText("verify-console", advisoryOnlyMessage());
  hide("verify-status");
  hide("merge-status");
  hide("save-status");
  hide("merge-console");
  hide("save-console");
}

function drawDetail() {
  var item = selectedItem();
  if (item === null) {
    return;
  }
  renderSidebar();
  renderBanner(item);
  renderContract(item);
  renderValidate(item);
  renderAdjudication(item);
  renderRemediation(item);
  renderLocalRepair(item);
  renderQueryHints(item);
  renderMerge(item);
}

Array.prototype.forEach.call(document.querySelectorAll(".tab-btn"), function(btn) {
  btn.addEventListener("click", function() {
    switchTab(btn.getAttribute("data-tab"));
  });
});

element("stig-filter").addEventListener("input", function() {
  renderSidebar();
});

element("severity-filter").addEventListener("change", function() {
  renderSidebar();
});

element("stig-list").addEventListener("click", function(evt) {
  var holder = evt.target.closest("[data-vid]");
  if (!holder) {
    return;
  }
  currentVid = holder.getAttribute("data-vid");
  drawDetail();
});

function initShell() {
  setText("sessLabel", "Certified packaged export");
  element("sessDot").classList.add("ok");
  setText("conn-status", "Packaged Export");
  element("conn-status").className = "conn-status on";
  element("sel-host").innerHTML = '<option value="packaged-export">Packaged export bundle</option>';
  element("inp-user").value = "projection-only";
  element("inp-pass").value = "disabled";
  element("inp-user").disabled = true;
  element("inp-pass").disabled = true;
  element("sel-host").disabled = true;
  element("btn-disconnect").classList.add("hidden");
  element("btn-connect").textContent = "Projection Only";
  element("btn-validate-all").disabled = true;
  setText("validate-all-progress", "Use the certified projected statuses already shown in the sidebar.");
  show("validate-all-progress");
  drawDetail();
}

initShell();
</script>"""


def build_html(bundle):
    embedded = json.dumps(bundle, indent=2)
    base = template_without_scripts()
    injection = (
        '<script type="application/json" id="projection-data">\n'
        + embedded
        + '\n</script>\n'
        + projection_script()
        + "\n</body>"
    )
    return base.replace("</body>", injection)


def write_html_export():
    bundle = load_projection_bundle()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    html_text = build_html(bundle)
    EXPORT_HTML_PATH.write_text(html_text, encoding="utf-8")
    js_blocks = extract_js_blocks(html_text)
    js_text = "\n".join(js_blocks)
    violations = [token for token in FORBIDDEN_JS_TOKENS if token in js_text]
    for token in violations:
        print(f"VIOLATION: {token} found in JS")
    if violations:
        raise SystemExit(1)
    print(
        f"export/stig_expert_critic.html written "
        f"({EXPORT_HTML_PATH.stat().st_size} bytes, {len(bundle)} controls embedded)"
    )
    return bundle


def main():
    write_html_export()


if __name__ == "__main__":
    main()

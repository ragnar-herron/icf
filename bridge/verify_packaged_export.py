import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPORT_HTML_PATH = ROOT / "export" / "stig_expert_critic.html"
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"
PACKAGE_DIR = ROOT / "factory_exports" / "stig_expert_critic"
PACKAGED_HTML_PATH = PACKAGE_DIR / "stig_expert_critic.html"
PACKAGED_LIVE_HTML_PATH = PACKAGE_DIR / "stig_remediation_tool.html"
PACKAGED_PROJECTION_HTML_PATH = PACKAGE_DIR / "stig_expert_critic_projection.html"
PACKAGED_PROJECTION_PATH = PACKAGE_DIR / "data" / "ProjectionBundle.json"
PACKAGED_WEB_APP_PATH = PACKAGE_DIR / "web_app.py"
PACKAGED_LIVE_WEB_APP_PATH = PACKAGE_DIR / "web_app_live.py"
PACKAGED_PROJECTION_WEB_APP_PATH = PACKAGE_DIR / "web_app_projection.py"
PACKAGED_LIVE_EVALUATOR_PATH = PACKAGE_DIR / "live_evaluator.py"
PACKAGED_F5_CLIENT_PATH = PACKAGE_DIR / "f5_client.py"

PROJECTION_FORBIDDEN_TOKENS = [
    "family_evaluator",
    "evidence_extractor",
    "fixture_runner",
    "parse_criteria",
    "eval(",
    "promote",
    "witness",
    "judge",
    "assess",
]

PROJECTION_FORBIDDEN_ROUTES = [
    "/api/validate",
    "/api/validate/all",
    "/api/remediate",
    "/api/merge",
]

PROJECTION_REQUIRED_ROUTES = [
    "/",
    "/api/projection_bundle",
    "/healthz",
]

LIVE_REQUIRED_ROUTES = [
    "/api/hosts",
    "/api/validate",
    "/api/validate/all",
]

LIVE_REQUIRED_TOKENS = [
    "F5Client",
    "live_evaluator",
    "def do_POST",
    "--mode",
    "live",
]


def main():
    if EXPORT_HTML_PATH.read_bytes() != PACKAGED_HTML_PATH.read_bytes():
        raise SystemExit("packaged html does not match certified export")
    if EXPORT_HTML_PATH.read_bytes() != PACKAGED_PROJECTION_HTML_PATH.read_bytes():
        raise SystemExit("packaged projection html does not match certified export")
    if PROJECTION_BUNDLE_PATH.read_bytes() != PACKAGED_PROJECTION_PATH.read_bytes():
        raise SystemExit("packaged projection bundle does not match certified bundle")

    for path in (
        PACKAGED_LIVE_HTML_PATH,
        PACKAGED_PROJECTION_HTML_PATH,
        PACKAGED_WEB_APP_PATH,
        PACKAGED_LIVE_WEB_APP_PATH,
        PACKAGED_PROJECTION_WEB_APP_PATH,
        PACKAGED_LIVE_EVALUATOR_PATH,
        PACKAGED_F5_CLIENT_PATH,
    ):
        if not path.exists():
            raise SystemExit(f"required packaged runtime file missing: {path}")

    live_source = PACKAGED_WEB_APP_PATH.read_text(encoding="utf-8")
    live_alias_source = PACKAGED_LIVE_WEB_APP_PATH.read_text(encoding="utf-8")
    if live_source != live_alias_source:
        raise SystemExit("web_app_live.py must match live web_app.py")
    for token in LIVE_REQUIRED_TOKENS:
        if token not in live_source:
            raise SystemExit(f"live runtime token missing: {token}")
    for route in LIVE_REQUIRED_ROUTES:
        if route not in live_source:
            raise SystemExit(f"live runtime route missing: {route}")
    if "projection-only" in live_source or "projection mode blocks live execution" in live_source:
        raise SystemExit("live runtime contains projection-only behavior")
    live_html = PACKAGED_LIVE_HTML_PATH.read_text(encoding="utf-8")
    if "projection-only" in live_html or "Live execution is not available" in live_html:
        raise SystemExit("live HTML contains projection-only behavior")
    if "/api/validate" not in live_html or "/api/hosts" not in live_html:
        raise SystemExit("live HTML does not reference live API routes")

    projection_source = PACKAGED_PROJECTION_WEB_APP_PATH.read_text(encoding="utf-8")
    for token in PROJECTION_FORBIDDEN_TOKENS:
        if token in projection_source:
            raise SystemExit(f"forbidden token found in projection wrapper: {token}")
    for route in PROJECTION_FORBIDDEN_ROUTES:
        if route in projection_source:
            raise SystemExit(f"forbidden live route found in projection wrapper: {route}")
    for route in PROJECTION_REQUIRED_ROUTES:
        if route not in projection_source:
            raise SystemExit(f"required projection route missing: {route}")
    if "projection mode blocks live execution" not in projection_source:
        raise SystemExit("projection wrapper does not explicitly block live execution")

    packager_source = (ROOT / "bridge" / "build_packaged_web_app.py").read_text(encoding="utf-8")
    if "PACKAGED_WEB_APP_PATH.write_text" in packager_source:
        raise SystemExit("packager overwrites live web_app.py")

    projection_bundle = json.loads(PACKAGED_PROJECTION_PATH.read_text(encoding="utf-8"))
    if len(projection_bundle) != 67:
        raise SystemExit("packaged projection bundle does not contain 67 entries")

    print("PACKAGED EXPORT: PASS")
    print("LIVE MODE: PASS (/api/hosts, /api/validate)")
    print("PROJECTION MODE: PASS (/api/projection_bundle, live execution blocked)")


if __name__ == "__main__":
    main()

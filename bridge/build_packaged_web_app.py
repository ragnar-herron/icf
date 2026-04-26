import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPORT_HTML_PATH = ROOT / "export" / "stig_expert_critic.html"
PROJECTION_BUNDLE_PATH = ROOT / "bridge" / "ProjectionBundle.json"
PACKAGE_DIR = ROOT / "factory_exports" / "stig_expert_critic"
PACKAGE_DATA_DIR = PACKAGE_DIR / "data"
PACKAGED_HTML_PATH = PACKAGE_DIR / "stig_expert_critic.html"
LEGACY_PACKAGED_HTML_PATH = PACKAGE_DIR / "stig_remediation_tool.html"
PACKAGED_PROJECTION_HTML_PATH = PACKAGE_DIR / "stig_expert_critic_projection.html"
PACKAGED_PROJECTION_PATH = PACKAGE_DATA_DIR / "ProjectionBundle.json"
PACKAGED_WEB_APP_PATH = PACKAGE_DIR / "web_app.py"
PACKAGED_LIVE_WEB_APP_PATH = PACKAGE_DIR / "web_app_live.py"
PACKAGED_PROJECTION_WEB_APP_PATH = PACKAGE_DIR / "web_app_projection.py"
PACKAGED_LIVE_EVALUATOR_PATH = PACKAGE_DIR / "live_evaluator.py"
PACKAGED_F5_CLIENT_PATH = PACKAGE_DIR / "f5_client.py"


PROJECTION_WEB_APP_SOURCE = """import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HTML_PATH = ROOT / "stig_expert_critic.html"
PROJECTION_HTML_PATH = ROOT / "stig_expert_critic_projection.html"
PROJECTION_PATH = ROOT / "data" / "ProjectionBundle.json"
HOST = os.environ.get("STIG_EXPORT_HOST", "127.0.0.1")
PORT = int(os.environ.get("STIG_EXPORT_PORT", "8000"))


def read_projection():
    return json.loads(PROJECTION_PATH.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/stig_expert_critic.html", "/stig_expert_critic_projection.html"):
            path = PROJECTION_HTML_PATH if self.path == "/stig_expert_critic_projection.html" and PROJECTION_HTML_PATH.exists() else HTML_PATH
            payload = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/api/projection_bundle":
            payload = PROJECTION_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/healthz":
            payload = json.dumps({
                "ok": True,
                "html": HTML_PATH.name,
                "projection_entries": len(read_projection()),
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(404)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"ok": false, "error": "not found"}')

    def do_POST(self):
        self.send_response(403)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'{"ok": false, "error": "projection mode blocks live execution"}')

    def log_message(self, fmt, *args):
        return


def main():
    parser = argparse.ArgumentParser(description="Projection-only STIG export server")
    parser.add_argument("--mode", default="projection", choices=("projection",))
    parser.parse_args()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"STIG projection-only web app listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
"""


def main():
    if not EXPORT_HTML_PATH.exists():
        raise FileNotFoundError(f"missing certified export html: {EXPORT_HTML_PATH}")
    if not PROJECTION_BUNDLE_PATH.exists():
        raise FileNotFoundError(f"missing projection bundle: {PROJECTION_BUNDLE_PATH}")

    PACKAGE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    for live_path in (
        PACKAGED_WEB_APP_PATH,
        PACKAGED_LIVE_EVALUATOR_PATH,
        PACKAGED_F5_CLIENT_PATH,
        LEGACY_PACKAGED_HTML_PATH,
    ):
        if not live_path.exists():
            raise FileNotFoundError(
                "missing live runtime file; packaging must not synthesize or "
                f"overwrite live runtime: {live_path}"
            )

    live_source = PACKAGED_WEB_APP_PATH.read_text(encoding="utf-8")
    if "/api/validate" not in live_source or "/api/hosts" not in live_source:
        raise RuntimeError("active web_app.py is not the live runtime")
    live_html = LEGACY_PACKAGED_HTML_PATH.read_text(encoding="utf-8")
    if "projection-only" in live_html or "Live execution is not available" in live_html:
        raise RuntimeError("stig_remediation_tool.html is not the live UI")

    shutil.copyfile(EXPORT_HTML_PATH, PACKAGED_HTML_PATH)
    shutil.copyfile(EXPORT_HTML_PATH, PACKAGED_PROJECTION_HTML_PATH)
    shutil.copyfile(PROJECTION_BUNDLE_PATH, PACKAGED_PROJECTION_PATH)
    shutil.copyfile(PACKAGED_WEB_APP_PATH, PACKAGED_LIVE_WEB_APP_PATH)
    PACKAGED_PROJECTION_WEB_APP_PATH.write_text(PROJECTION_WEB_APP_SOURCE, encoding="utf-8")

    projection_bundle = json.loads(PACKAGED_PROJECTION_PATH.read_text(encoding="utf-8"))
    print(
        "PACKAGED WEB APP WRITTEN "
        f"({PACKAGED_HTML_PATH}, {PACKAGED_PROJECTION_HTML_PATH}, {LEGACY_PACKAGED_HTML_PATH}, "
        f"{PACKAGED_LIVE_WEB_APP_PATH}, {PACKAGED_PROJECTION_WEB_APP_PATH}, "
        f"{PACKAGED_PROJECTION_PATH}, {len(projection_bundle)} entries)"
    )


if __name__ == "__main__":
    main()

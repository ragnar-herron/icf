import argparse
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

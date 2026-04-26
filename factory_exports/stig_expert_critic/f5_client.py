"""
Tiny F5 iControl-REST client used by the live break/fix driver.

Intentionally stdlib-only (no `requests` dependency) so the live test can run
on any machine that already has Python 3. Certificate verification is
DISABLED because BIG-IP management uses a self-signed TLS certificate by
default. This is honest for a demo; a production upgrade MUST pin the TLS
fingerprint (see docs/BUILD_SPEC.md transport section).
"""
from __future__ import annotations

import base64
import json
import os
import shlex
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


class F5Client:
    def __init__(
        self,
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 20,
    ) -> None:
        self.host = host or os.environ["F5_host"]
        self.user = user or os.environ["F5_user"]
        self.password = password or os.environ["F5_password"]
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE
        token = base64.b64encode(
            f"{self.user}:{self.password}".encode("utf-8")
        ).decode("ascii")
        self._auth_header = f"Basic {token}"

    def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"https://{self.host}{path}"
        data = None
        headers = {
            "Authorization": self._auth_header,
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url=url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, context=self._ctx, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                code = resp.status
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8", errors="replace") if err.fp else ""
            raise RuntimeError(
                f"{method} {path} failed: HTTP {err.code} {err.reason}: {raw}"
            ) from err
        if code != 200:
            raise RuntimeError(f"{method} {path} returned HTTP {code}: {raw}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as err:
            raise RuntimeError(
                f"{method} {path} returned non-JSON body (len={len(raw)}): {raw[:200]!r}"
            ) from err

    def get(self, path: str) -> Dict[str, Any]:
        return self._request("GET", path)

    def patch(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PATCH", path, body)

    def post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", path, body)

    @staticmethod
    def _command_result(payload: Dict[str, Any], endpoint: str, command: str) -> str:
        output = payload.get("commandResult")
        if isinstance(output, str):
            return output
        # Some BIG-IP versions echo a util runstate object without commandResult
        # when the chosen util endpoint cannot execute the command.  Report that
        # clearly so callers know this is a transport/permission response, not a
        # missing local deployment file.
        raise RuntimeError(
            f"{endpoint} did not return commandResult for {command!r}; "
            f"payload={payload!r}"
        )

    def path_exists(self, path: str) -> bool:
        try:
            self.get(path)
            return True
        except RuntimeError as err:
            if "HTTP 404" in str(err):
                return False
            raise

    def run_bash(self, command: str) -> str:
        util_args = "-c " + shlex.quote(command)
        result = self.post(
            "/mgmt/tm/util/bash",
            {
                "command": "run",
                "utilCmdArgs": util_args,
            },
        )
        return self._command_result(result, "util/bash", command)

    def run_tmsh(self, command: str) -> str:
        safe = command.strip()
        if not safe.startswith("tmsh "):
            safe = f"tmsh {safe}"
        tmsh_command = safe[len("tmsh "):].strip()
        try:
            result = self.post(
                "/mgmt/tm/util/tmsh",
                {
                    "command": "run",
                    "utilCmdArgs": "-c " + shlex.quote(tmsh_command),
                },
            )
            return self._command_result(result, "util/tmsh", tmsh_command)
        except RuntimeError:
            # Older or restricted BIG-IP images may not expose util/tmsh
            # consistently.  Bash remains the compatibility fallback.
            return self.run_bash(safe)

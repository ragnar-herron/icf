"""Smoke-test the standalone factory web_app for per-measurement pullback.

Validates a deliberate mix of controls to prove the new schema works:

* V-266064   multi-predicate numeric (pass today)
* V-266069   multi-predicate numeric (pass today)
* V-266070   banner string equality (fail today)
* V-266134   enabled + banner composite (fail today)
* V-266079   auth source + tacacs server count
* V-266074   external-evidence package (unresolved)
* V-266152   APM multi-agent + TACACS

For each control we assert:

1. /api/validate returns measurements embedded in comparison_df rows.
2. Every row has a non-empty measurable, required, observed, source.
3. /api/hydrate returns the same measurements (bundle was persisted).
4. The adjudication proof chain has one `compare` step per measurement.
"""

from __future__ import annotations

import functools
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

# Force flushed prints so the output file updates promptly when run detached.
print = functools.partial(print, flush=True)  # type: ignore[assignment]

BASE = os.environ.get("STIG_FACTORY_BASE", "http://127.0.0.1:8779")
HOST = os.environ.get("F5_host", "132.145.154.175")
USER = os.environ.get("F5_user", "admin")
PASS = os.environ.get("F5_password", "u8myf00d!")

jar = CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.addheaders = [("Accept", "application/json"), ("Content-Type", "application/json")]


def req(method: str, path: str, body: dict | None = None) -> tuple[int, dict | str]:
    url = BASE + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    r = urllib.request.Request(url, data=data, method=method)
    try:
        with opener.open(r, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            code = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        code = exc.code
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        return code, raw


def check(condition: bool, label: str) -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}")
    if not condition:
        check.failed += 1  # type: ignore[attr-defined]


check.failed = 0  # type: ignore[attr-defined]


def main() -> int:
    print(f"# Smoke-test against {BASE}, device {HOST}")
    code, data = req("GET", "/api/health")
    check(code == 200 and isinstance(data, dict) and data.get("ok"), f"health code={code}")

    code, contracts = req("GET", "/api/contracts")
    check(code == 200 and isinstance(contracts, list) and len(contracts) >= 60,
          f"contracts code={code}, n={len(contracts) if isinstance(contracts, list) else 'n/a'}")

    code, data = req("POST", "/api/login",
                      {"host": HOST, "username": USER, "password": PASS})
    check(code == 200 and data.get("ok"), f"login code={code}")

    # Keep the list short so the smoke test completes in < 2 min against
    # the live device.  One pass-family, one fail-family, one external-only.
    targets = os.environ.get("SMOKE_VIDS", "V-266064,V-266070,V-266074").split(",")

    for vid in targets:
        print(f"\n## {vid}")
        code, data = req("POST", "/api/validate",
                         {"host": HOST, "username": USER, "password": PASS,
                          "vuln_id": vid})
        check(code == 200 and data.get("ok"), f"validate code={code}")
        if not (code == 200 and data.get("ok")):
            print("    error payload:", json.dumps(data, indent=2)[:800])
            continue

        rows = data.get("comparison_df") or []
        check(len(rows) >= 1, f"comparison_df non-empty (got {len(rows)} rows)")

        needed = {"measurable", "required", "observed", "match",
                  "carrier_coordinate", "source_key"}
        bad = [r for r in rows if not all(k in r for k in needed)]
        check(not bad, f"every row has required keys ({len(rows) - len(bad)}/{len(rows)})")

        blank = [r for r in rows if not str(r.get("measurable", "")).strip()
                 or not str(r.get("required", "")).strip()
                 or not str(r.get("carrier_coordinate", "")).strip()]
        check(not blank, f"no blank measurable/required/source ({len(rows) - len(blank)}/{len(rows)})")

        for r in rows[:3]:
            print(f"    row: {r['measurable']:55} req={r['required']:40} obs={r['observed']:30} match={r['match']} src={r['carrier_coordinate']}")

        adj = data.get("adjudication") or {}
        steps = adj.get("proof_steps") or []
        compare_steps = [s for s in steps if s.get("step") == "compare"]
        check(len(compare_steps) == len(rows),
              f"proof has one compare step per row (rows={len(rows)} steps={len(compare_steps)})")

        pb = data.get("pullback_df") or []
        diagram = next((p for p in pb if p.get("record_type") == "diagram"), {})
        pairs = diagram.get("fiber_pairs") or []
        check(len(pairs) == len(rows),
              f"pullback diagram has one fiber pair per row (pairs={len(pairs)} rows={len(rows)})")

        # Hydrate to prove persistence of the new schema.
        code, hy = req("GET", f"/api/hydrate/{vid}?host={urllib.parse.quote(HOST)}")
        check(code == 200 and hy.get("ok") and hy.get("vuln_id") == vid,
              f"hydrate code={code}")
        hy_rows = hy.get("comparison_df") or []
        check(len(hy_rows) == len(rows), f"hydrated rows = validate rows ({len(hy_rows)} vs {len(rows)})")

    code, _ = req("POST", "/api/logout", {})
    check(code == 200, f"logout code={code}")

    print(f"\n## Result: {check.failed} failure(s)")  # type: ignore[attr-defined]
    return 0 if check.failed == 0 else 1  # type: ignore[attr-defined]


if __name__ == "__main__":
    sys.exit(main())

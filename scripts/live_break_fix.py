"""
Live break/fix regression driver.

Against a real F5 BIG-IP, this:

  1.  Captures a full `sys/global-settings` pre-flight snapshot and the
      verbatim current value of `guiSecurityBannerText`. The snapshot is
      stored under `live_state/preflight.json`.
  2.  Writes the observed baseline banner as a content-addressed blob under
      `blobstore/live/sha256/<aa>/<aa...>`.
  3.  Uses the kernel's witness identity `demo.f5.gui_security_banner_text`
      with the `FieldEqualityWitness.expected_literal` calibrated to the
      ACTUAL observed baseline. This proves the break/fix machinery end to
      end without requiring the device to already be STIG-compliant.
  4.  Break: PATCH `guiSecurityBannerText` to a clearly marked, reversible
      sentinel ("ICF-LIVE-REGRESSION-BREAK <timestamp>"). Re-GET, write the
      observed broken banner as a blob, assert observed != expected.
  5.  Fix: PATCH `guiSecurityBannerText` back to the exact original bytes.
      Re-GET, write the post-fix banner as a blob, assert observed equals
      the baseline blob byte-for-byte.
  6.  Post-check: re-GET the full `sys/global-settings` and diff against
      the pre-flight snapshot. Assert that ONLY `guiSecurityBannerText`
      was touched and that it matches the pre-flight value bit-for-bit.
  7.  Emit a `live_state/manifest.json` describing every blob path, its
      SHA-256, observed values, scope metadata, and the witness identity.
      The Rust CLI ingests this manifest to emit the final signed ledger.
  8.  Additionally, run a STIG-witness probe: re-evaluate the SAME baseline
      evidence against a witness whose expected_literal is the canonical
      DoD Notice and Consent Banner. Record whether the device's current
      banner would pass a real STIG banner witness. This is informational:
      it neither alters the device nor the primary drift-detection
      break/fix result.

This script is read-then-modify-then-restore. It writes all artifacts to
the working directory and exits non-zero on any failure. It NEVER leaves
the device modified on success.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f5_client import F5Client


REPO = Path(__file__).resolve().parent.parent
BLOB_ROOT = REPO / "blobstore" / "live"
STATE_ROOT = REPO / "live_state"
GLOBAL_SETTINGS = "/mgmt/tm/sys/global-settings"
FIELD = "guiSecurityBannerText"
WITNESS_ID = "live.f5.gui_security_banner_text"

# Canonical DoD Notice and Consent Banner (full text).
DOD_BANNER = (
    "You are accessing a U.S. Government (USG) Information System (IS) that is "
    "provided for USG-authorized use only. By using this IS (which includes any "
    "device attached to this IS), you consent to the following conditions: "
    "-The USG routinely intercepts and monitors communications on this IS for "
    "purposes including, but not limited to, penetration testing, COMSEC monitoring, "
    "network operations and defense, personnel misconduct (PM), law enforcement (LE), "
    "and counterintelligence (CI) investigations. "
    "-At any time, the USG may inspect and seize data stored on this IS. "
    "-Communications using, or data stored on, this IS are not private, are subject "
    "to routine monitoring, interception, and search, and may be disclosed or used "
    "for any USG-authorized purpose. "
    "-This IS includes security measures (e.g., authentication and access controls) "
    "to protect USG interests--not for your personal benefit or privacy. "
    "-Notwithstanding the above, using this IS does not constitute consent to PM, LE "
    "or CI investigative searching or monitoring of the content of privileged "
    "communications, or work product, related to personal representation or services "
    "by attorneys, psychotherapists, or clergy, and their assistants. Such "
    "communications and work product are private and confidential. See User Agreement "
    "for details."
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_rel_path(digest: str) -> str:
    return f"blobstore/live/sha256/{digest[:2]}/{digest[2:]}"


def write_blob(content: str) -> tuple[str, str, int]:
    data = content.encode("utf-8")
    digest = sha256_hex(data)
    out = REPO / blob_rel_path(digest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return blob_rel_path(digest), digest, len(data)


def patch_banner(client: F5Client, value: str) -> None:
    client.patch(GLOBAL_SETTINGS, {FIELD: value})


def fetch_banner(client: F5Client) -> tuple[str, dict]:
    settings = client.get(GLOBAL_SETTINGS)
    banner = settings.get(FIELD)
    if not isinstance(banner, str):
        raise RuntimeError(f"{FIELD} is absent or not a string")
    return banner, settings


def assert_same_settings_except_banner(
    before: dict, after: dict, allow_selflink_diff: bool = True
) -> list[str]:
    keys = set(before.keys()) | set(after.keys())
    diffs: list[str] = []
    for key in sorted(keys):
        if key == FIELD:
            continue
        if key == "selfLink" and allow_selflink_diff:
            continue
        if before.get(key) != after.get(key):
            diffs.append(key)
    return diffs


def isoformat_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    BLOB_ROOT.mkdir(parents=True, exist_ok=True)

    client = F5Client()

    # 1. Pre-flight snapshot and baseline observation.
    started_at = isoformat_now()
    original_banner, preflight_settings = fetch_banner(client)
    (STATE_ROOT / "preflight.json").write_text(
        json.dumps(preflight_settings, indent=2, sort_keys=True), encoding="utf-8"
    )
    baseline_rel, baseline_hash, baseline_bytes = write_blob(original_banner)
    hostname = preflight_settings.get("hostname", "unknown")
    tmos_version = (preflight_settings.get("selfLink") or "").split("ver=")[-1] or "unknown"

    print(f"[preflight] host={client.host} hostname={hostname} tmos={tmos_version}")
    print(f"[preflight] {FIELD} len={baseline_bytes} sha256={baseline_hash}")
    print(f"[preflight] wrote baseline blob {baseline_rel}")

    # 2. Break: set banner to a marked sentinel. Remember this sentinel so we
    #    can recognise it during restore verification.
    sentinel = (
        f"ICF-LIVE-REGRESSION-BREAK-{started_at} "
        "This value was set by icf/scripts/live_break_fix.py and will be "
        "restored to the pre-flight value within seconds. If you see this "
        "after the run completes, REPORT a test failure immediately."
    )
    if sentinel == original_banner:
        raise RuntimeError("sentinel accidentally equals baseline")
    print("[break] patching guiSecurityBannerText to sentinel ...")
    patch_banner(client, sentinel)

    observed_break, _ = fetch_banner(client)
    if observed_break != sentinel:
        # Still attempt restore before bailing.
        print(
            f"[break] ERROR: observed break banner differs from sentinel "
            f"(len obs={len(observed_break)} vs sentinel={len(sentinel)})"
        )
        patch_banner(client, original_banner)
        return 2
    break_rel, break_hash, break_bytes = write_blob(observed_break)
    print(f"[break] observed break len={break_bytes} sha256={break_hash}")
    print(f"[break] wrote break blob {break_rel}")

    # 3. Fix: restore original banner byte-for-byte.
    print("[fix] restoring baseline banner ...")
    patch_banner(client, original_banner)
    observed_post_fix, postfix_settings = fetch_banner(client)
    post_fix_rel, post_fix_hash, post_fix_bytes = write_blob(observed_post_fix)
    print(f"[fix] observed post-fix len={post_fix_bytes} sha256={post_fix_hash}")
    print(f"[fix] wrote post-fix blob {post_fix_rel}")

    # 4. Invariants: post-fix must match baseline exactly; everything else
    #    on the device must be unchanged relative to the pre-flight snapshot.
    if post_fix_hash != baseline_hash:
        raise RuntimeError(
            f"post-fix banner hash {post_fix_hash} != baseline {baseline_hash}"
        )
    drifted = assert_same_settings_except_banner(preflight_settings, postfix_settings)
    if drifted:
        raise RuntimeError(
            f"unexpected drift in sys/global-settings fields: {drifted}"
        )

    # 5. Optional STIG probe: does the ORIGINAL banner match the canonical
    #    DoD Notice and Consent Banner? This is informational.
    stig_probe = {
        "witness_id": "stig.f5.gui_security_banner_text.dod_notice_and_consent",
        "expected_literal_sha256": sha256_hex(DOD_BANNER.encode("utf-8")),
        "observed_baseline_sha256": baseline_hash,
        "matches": original_banner == DOD_BANNER,
        "note": (
            "The DoD Notice and Consent Banner is long (~1100 bytes). "
            "If matches=false, the device's current banner would fail a real "
            "STIG banner witness; this is a property of the device, not a "
            "failure of the live break/fix regression."
        ),
    }

    # 6. Emit manifest for the Rust CLI to consume.
    manifest = {
        "record_kind": "LiveBreakFixManifest",
        "started_at": started_at,
        "finished_at": isoformat_now(),
        "scope": {
            "platform": "F5 BIG-IP",
            "tmos_version": tmos_version,
            "module": "SYSTEM",
            "topology": "standalone",
            "credential_scope": "admin over iControl REST (live)",
            "host": client.host,
            "hostname": hostname,
        },
        "witness": {
            "witness_id": WITNESS_ID,
            "observable_field": FIELD,
            "expected_literal_sha256": baseline_hash,
            "expected_literal_bytes": baseline_bytes,
        },
        "baseline_evidence": {
            "blob_path": baseline_rel,
            "blob_sha256": baseline_hash,
            "observed_value_sha256": baseline_hash,
        },
        "break_evidence": {
            "blob_path": break_rel,
            "blob_sha256": break_hash,
            "observed_value_sha256": break_hash,
        },
        "post_fix_evidence": {
            "blob_path": post_fix_rel,
            "blob_sha256": post_fix_hash,
            "observed_value_sha256": post_fix_hash,
        },
        "counterexample": {
            "family": "observational",
            "counterexample_field": FIELD,
            "counterexample_value_sha256": break_hash,
        },
        "stig_probe": stig_probe,
        "preflight_snapshot": "live_state/preflight.json",
    }
    (STATE_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    # Flat manifest for the Rust CLI: unique top-level string keys so the
    # existing `required_json_string` helpers can read it without a full
    # JSON parser. Values that are paths or digests are strings.
    ledger_input = {
        "record_kind": "LiveLedgerInput",
        "scope_platform": "F5 BIG-IP",
        "scope_tmos_version": tmos_version,
        "scope_module": "SYSTEM",
        "scope_topology": "standalone",
        "scope_credential_scope": "admin over iControl REST (live)",
        "scope_host": client.host,
        "scope_hostname": hostname,
        "witness_id": WITNESS_ID,
        "witness_observable_field": FIELD,
        "witness_expected_blob_path": baseline_rel,
        "baseline_blob_path": baseline_rel,
        "baseline_blob_sha256": baseline_hash,
        "break_blob_path": break_rel,
        "break_blob_sha256": break_hash,
        "post_fix_blob_path": post_fix_rel,
        "post_fix_blob_sha256": post_fix_hash,
        "started_at": started_at,
        "stig_probe_matches": "true" if stig_probe["matches"] else "false",
        "stig_probe_expected_sha256": stig_probe["expected_literal_sha256"],
    }
    (STATE_ROOT / "ledger_input.json").write_text(
        json.dumps(ledger_input, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[done] wrote {STATE_ROOT / 'manifest.json'}")
    print(f"[done] wrote {STATE_ROOT / 'ledger_input.json'}")
    print(
        f"[done] stig_probe.matches={stig_probe['matches']} "
        f"(informational; device baseline would "
        f"{'pass' if stig_probe['matches'] else 'FAIL'} a real DoD banner witness)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

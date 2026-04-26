from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime

from backup_external_evidence import BACKUP_LOCAL_EVIDENCE_PATH
from f5_client import F5Client


def now_utc() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def main() -> None:
    host = os.environ.get("F5_host") or os.environ.get("STIG_F5_HOST")
    username = os.environ.get("F5_user") or os.environ.get("STIG_F5_USER")
    password = os.environ.get("F5_password") or os.environ.get("STIG_F5_PASSWORD")
    if not host or not username or not password:
        raise SystemExit("missing credentials: set F5_host/F5_user/F5_password")

    client = F5Client(host, username, password)
    output = client.run_tmsh("list sys ucs")
    archives = []
    current: dict[str, str] | None = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if line == "sys ucs {":
            current = {}
            continue
        if line == "}":
            if current is not None:
                archives.append(current)
            current = None
            continue
        if current is None:
            continue
        match = re.match(r"([A-Za-z0-9_]+)\s+(.+)", line)
        if match:
            current[match.group(1)] = match.group(2)

    payload = {
        "record_type": "BackupLocalEvidence",
        "captured_at": now_utc(),
        "host": host,
        "backup_archive_count": len(archives),
        "local_backup_exists": len(archives) > 0,
        "archives": archives,
        "source_command": "tmsh list sys ucs",
    }
    BACKUP_LOCAL_EVIDENCE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(str(BACKUP_LOCAL_EVIDENCE_PATH))


if __name__ == "__main__":
    main()

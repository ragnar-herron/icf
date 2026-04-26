from __future__ import annotations

import json

from backup_external_evidence import backup_external_evidence_status, backup_local_evidence_status, build_backup_combined_measurable


def main() -> None:
    payload = {
        "external": backup_external_evidence_status(),
        "local": backup_local_evidence_status(),
        "combined": build_backup_combined_measurable(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()

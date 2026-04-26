from __future__ import annotations

import json

from backup_external_evidence import BACKUP_COMBINED_MEASURABLE_PATH, build_backup_combined_measurable


def main() -> None:
    payload = build_backup_combined_measurable()
    BACKUP_COMBINED_MEASURABLE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(str(BACKUP_COMBINED_MEASURABLE_PATH))


if __name__ == "__main__":
    main()

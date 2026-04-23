#!/usr/bin/env python3
from __future__ import annotations

from artifact_inventory_record_schema import validate_artifact_inventory_record
from web_app import artifact_inventory_record


def main() -> int:
    record = artifact_inventory_record()
    errors = validate_artifact_inventory_record(record)
    if errors:
        print(f"artifact_inventory_record=FAIL::{' ; '.join(errors)}")
        return 1
    print(f"artifact_inventory_record=PASS::{record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

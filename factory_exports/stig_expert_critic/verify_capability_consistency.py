#!/usr/bin/env python3
from __future__ import annotations

from capability_consistency_record_schema import validate_capability_consistency_record
from web_app import capability_consistency_record


def main() -> int:
    record = capability_consistency_record()
    errors = validate_capability_consistency_record(record)
    if errors:
        print(f"capability_consistency=FAIL::{' ; '.join(errors)}")
        return 1
    if record["status"] != "pass":
        for item in record["inconsistencies"]:
            print(f"inconsistency={item['vid']}::{item['issue']}")
        print(f"capability_consistency=FAIL::{record['summary']}")
        return 1
    print(f"capability_consistency=PASS::{record['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

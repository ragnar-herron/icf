#!/usr/bin/env python3
from __future__ import annotations

from promotion_priority_queue_record_schema import validate_promotion_priority_queue_record
from web_app import promotion_priority_queue_record


def main() -> int:
    record = promotion_priority_queue_record()
    errors = validate_promotion_priority_queue_record(record)
    if errors:
        print(f"promotion_priority_queue=FAIL::{' ; '.join(errors)}")
        return 1
    print(f"promotion_priority_queue=PASS::{record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

from promotion_work_order_record_schema import validate_promotion_work_order_record
from web_app import promotion_work_order_record


def main() -> int:
    record = promotion_work_order_record()
    errors = validate_promotion_work_order_record(record)
    if errors:
        print(f"promotion_work_order=FAIL::{' ; '.join(errors)}")
        return 1
    print(f"promotion_work_order=PASS::{record['family']}::{record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

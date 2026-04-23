#!/usr/bin/env python3
from __future__ import annotations

from enforcement_rules import enforcement_summary


def main() -> int:
    report = enforcement_summary()
    for item in report["grandfathered"]:
        print(f"grandfathered={item['rule_id']}::{item['file']}::{item['snippet']}")
    for item in report["violations"]:
        print(f"violation={item['rule_id']}::{item['file']}::{item['snippet']}")
    print(f"enforcement_summary={report['summary']}")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

from legitimacy_record_schema import validate_legitimacy_record
from web_app import legitimacy_record_for_control
from live_evaluator import load_catalog


def main() -> int:
    errors = 0
    for control in load_catalog().values():
        record = legitimacy_record_for_control(control)
        problems = validate_legitimacy_record(record)
        if problems:
            errors += 1
            print(f"legitimacy_record=FAIL::{control['vuln_id']}::{'; '.join(problems)}")
            continue
        print(f"legitimacy_record=PASS::{control['vuln_id']}::{record['status']}")
    print(f"legitimacy_records={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

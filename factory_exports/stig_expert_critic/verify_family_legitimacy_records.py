#!/usr/bin/env python3
from __future__ import annotations

from family_legitimacy_record_schema import validate_family_legitimacy_record
from web_app import adapter_family_for_control, family_legitimacy_record_for_family
from live_evaluator import load_catalog


def main() -> int:
    errors = 0
    families = sorted({adapter_family_for_control(control) for control in load_catalog().values()})
    for family in families:
        record = family_legitimacy_record_for_family(family)
        problems = validate_family_legitimacy_record(record)
        if problems:
            errors += 1
            print(f"family_legitimacy_record=FAIL::{family}::{'; '.join(problems)}")
            continue
        print(f"family_legitimacy_record=PASS::{family}::{record['status']}")
    print(f"family_legitimacy_records={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

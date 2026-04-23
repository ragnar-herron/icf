#!/usr/bin/env python3
from __future__ import annotations

from evidence_backlog_record_schema import validate_evidence_backlog_record
from web_app import (
    adapter_family_for_control,
    control_evidence_backlog_record,
    family_evidence_backlog_record,
)
from live_evaluator import load_catalog


def main() -> int:
    errors = 0
    catalog = load_catalog()
    for control in catalog.values():
        record = control_evidence_backlog_record(control)
        problems = validate_evidence_backlog_record(record)
        if problems:
            errors += 1
            print(f"control_backlog=FAIL::{control['vuln_id']}::{'; '.join(problems)}")
        else:
            print(f"control_backlog=PASS::{control['vuln_id']}::{record['status']}")
    families = sorted({adapter_family_for_control(control) for control in catalog.values()})
    for family in families:
        record = family_evidence_backlog_record(family)
        problems = validate_evidence_backlog_record(record)
        if problems:
            errors += 1
            print(f"family_backlog=FAIL::{family}::{'; '.join(problems)}")
        else:
            print(f"family_backlog=PASS::{family}::{record['status']}")
    print(f"evidence_backlog_records={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

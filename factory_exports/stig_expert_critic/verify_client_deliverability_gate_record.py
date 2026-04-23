#!/usr/bin/env python3
from __future__ import annotations

from client_deliverability_gate_record_schema import validate_client_deliverability_gate_record
from web_app import client_deliverability_gate_record


def main() -> int:
    record = client_deliverability_gate_record()
    errors = validate_client_deliverability_gate_record(record)
    if errors:
        print(f"client_deliverability=FAIL::{' ; '.join(errors)}")
        return 1
    print(f"client_deliverability=PASS::{record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

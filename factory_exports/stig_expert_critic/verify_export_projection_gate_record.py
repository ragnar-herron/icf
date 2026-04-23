#!/usr/bin/env python3
from __future__ import annotations

from export_projection_gate_record_schema import validate_export_projection_gate_record
from web_app import export_projection_gate_record


def main() -> int:
    record = export_projection_gate_record()
    errors = validate_export_projection_gate_record(record)
    if errors:
        print(f"export_projection_gate_record=FAIL::{' ; '.join(errors)}")
        return 1
    print(f"export_projection_gate_record=PASS::{record['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from live_evaluator import load_catalog
from web_app import (
    adapter_family_for_control,
    control_evidence_backlog_record,
    family_evidence_backlog_record,
)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: generate_evidence_backlog_record.py <control|family> <id>")
        return 1
    subject_type = argv[1].strip().lower()
    subject_id = argv[2].strip()
    catalog = load_catalog()
    if subject_type == "control":
        vid = subject_id.upper()
        if vid not in catalog:
            print(f"unknown V-ID: {vid}")
            return 1
        record = control_evidence_backlog_record(catalog[vid])
    elif subject_type == "family":
        families = {adapter_family_for_control(control) for control in catalog.values()}
        if subject_id not in families:
            print(f"unknown family: {subject_id}")
            return 1
        record = family_evidence_backlog_record(subject_id)
    else:
        print("subject type must be control or family")
        return 1
    print(json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

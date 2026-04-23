#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from live_evaluator import load_catalog
from web_app import legitimacy_record_for_control


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: generate_legitimacy_record.py <V-ID>")
        return 1
    vid = argv[1].strip().upper()
    catalog = load_catalog()
    if vid not in catalog:
        print(f"unknown V-ID: {vid}")
        return 1
    print(json.dumps(legitimacy_record_for_control(catalog[vid]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

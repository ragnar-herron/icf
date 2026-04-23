#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from web_app import family_legitimacy_record_for_family
from live_evaluator import load_catalog
from web_app import adapter_family_for_control


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: generate_family_legitimacy_record.py <family>")
        return 1
    family = argv[1].strip()
    families = {adapter_family_for_control(control) for control in load_catalog().values()}
    if family not in families:
        print(f"unknown family: {family}")
        return 1
    print(json.dumps(family_legitimacy_record_for_family(family), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

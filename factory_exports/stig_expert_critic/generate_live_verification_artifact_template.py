#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from live_evaluator import load_catalog
from live_verification_template import live_verification_artifact_template
from web_app import adapter_family_for_control


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: generate_live_verification_artifact_template.py <V-ID>")
        return 1
    vid = argv[1].strip().upper()
    catalog = load_catalog()
    if vid not in catalog:
        print(f"unknown V-ID: {vid}")
        return 1
    control = catalog[vid]
    template = live_verification_artifact_template(vid, adapter_family_for_control(control))
    print(json.dumps(template, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

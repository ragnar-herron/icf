#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

import web_app
from promotion_template import promotion_artifact_template


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: generate_promotion_artifact_template.py <V-ID>")
        return 2
    vid = argv[1].strip()
    if vid not in web_app.SAFE_VID:
        print("invalid vid")
        return 2
    control = web_app.load_catalog()[vid]
    family = web_app.adapter_family_for_control(control)
    print(json.dumps(promotion_artifact_template(vid, family), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

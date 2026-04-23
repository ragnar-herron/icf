#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from promotion_artifact_schema import validate_promotion_artifact


ROOT = Path(__file__).resolve().parent
PROMOTIONS = ROOT / "promotions"


def main() -> int:
    artifacts = sorted(PROMOTIONS.glob("*.promotion.json"))
    if not artifacts:
        print("promotion_artifacts=NONE")
        return 0
    errors = 0
    for path in artifacts:
        doc = json.loads(path.read_text(encoding="utf-8"))
        problems = validate_promotion_artifact(doc)
        if problems:
            errors += 1
            print(f"promotion_artifact=FAIL::{path.name}::{'; '.join(problems)}")
        else:
            print(f"promotion_artifact=PASS::{path.name}")
    print(f"promotion_artifacts={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

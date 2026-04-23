#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from live_verification_artifact_schema import validate_live_verification_artifact


ROOT = Path(__file__).resolve().parent
LIVE_VERIFICATIONS = ROOT / "live_verifications"


def main() -> int:
    artifacts = sorted(LIVE_VERIFICATIONS.glob("*.live.json"))
    if not artifacts:
        print("live_verification_artifacts=NONE")
        return 0
    errors = 0
    for path in artifacts:
        doc = json.loads(path.read_text(encoding="utf-8"))
        problems = validate_live_verification_artifact(doc)
        if problems:
            errors += 1
            print(f"live_verification_artifact=FAIL::{path.name}::{'; '.join(problems)}")
        else:
            print(f"live_verification_artifact=PASS::{path.name}")
    print(f"live_verification_artifacts={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

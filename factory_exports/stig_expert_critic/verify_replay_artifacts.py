#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from replay_artifact_schema import validate_replay_artifact


ROOT = Path(__file__).resolve().parent
REPLAYS = ROOT / "replays"


def main() -> int:
    artifacts = sorted(REPLAYS.glob("*.replay.json"))
    if not artifacts:
        print("replay_artifacts=NONE")
        return 0
    errors = 0
    for path in artifacts:
        doc = json.loads(path.read_text(encoding="utf-8"))
        problems = validate_replay_artifact(doc)
        if problems:
            errors += 1
            print(f"replay_artifact=FAIL::{path.name}::{'; '.join(problems)}")
        else:
            print(f"replay_artifact=PASS::{path.name}")
    print(f"replay_artifacts={'PASS' if errors == 0 else 'FAIL'}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

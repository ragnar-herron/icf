from __future__ import annotations

import json
from pathlib import Path

from control_resolution import CONTROL_RESOLUTION_MAP


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "data" / "ControlResolutionClasses.json"


def main() -> None:
    payload = {
        "record_type": "ControlResolutionClasses",
        "controls": [
            {
                "vuln_id": vuln_id,
                **details,
            }
            for vuln_id, details in sorted(CONTROL_RESOLUTION_MAP.items())
        ],
    }
    TARGET.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(str(TARGET))


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
from pathlib import Path

from web_app import client_deliverability_gate


ROOT = Path(__file__).resolve().parent


def main() -> None:
    gate = client_deliverability_gate()
    target = ROOT / "data" / "ClientDeliverabilityGateRecord.json"
    target.write_text(json.dumps(gate, indent=2), encoding="utf-8")
    print(str(target))


if __name__ == "__main__":
    main()

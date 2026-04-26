from __future__ import annotations

import json
from pathlib import Path

from web_app import live_coverage_inventory, support_summary


ROOT = Path(__file__).resolve().parent


def main() -> None:
    inventory = live_coverage_inventory()
    summary = support_summary()
    output = {
        "summary": summary,
        "inventory": inventory,
    }
    target = ROOT / "data" / "LiveCoverageInventory.json"
    target.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(str(target))


if __name__ == "__main__":
    main()

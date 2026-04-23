#!/usr/bin/env python3
from __future__ import annotations

import json

from web_app import artifact_inventory_record


def main() -> int:
    print(json.dumps(artifact_inventory_record(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

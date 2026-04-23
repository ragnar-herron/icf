#!/usr/bin/env python3
from __future__ import annotations

import json
import sys

from web_app import promotion_work_order_record


def main(argv: list[str]) -> int:
    family = argv[1].strip() if len(argv) > 1 else None
    print(json.dumps(promotion_work_order_record(family), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

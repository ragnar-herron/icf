#!/usr/bin/env python3
from __future__ import annotations

import json

from web_app import capability_consistency_record


def main() -> int:
    print(json.dumps(capability_consistency_record(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

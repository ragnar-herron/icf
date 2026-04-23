#!/usr/bin/env python3
from __future__ import annotations

import json

from web_app import client_deliverability_gate_record


def main() -> int:
    print(json.dumps(client_deliverability_gate_record(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

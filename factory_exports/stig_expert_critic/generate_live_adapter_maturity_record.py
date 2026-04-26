from __future__ import annotations

import json

from live_adapter_promotion import BANNER_BUNDLE_PATH, BANNER_MATURITY_PATH, build_banner_promotion_bundle, build_live_adapter_maturity_record, load_json


def main() -> None:
    if BANNER_BUNDLE_PATH.exists():
        bundle = load_json(BANNER_BUNDLE_PATH)
    else:
        bundle = build_banner_promotion_bundle()
        BANNER_BUNDLE_PATH.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    record = build_live_adapter_maturity_record(bundle)
    BANNER_MATURITY_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(str(BANNER_MATURITY_PATH))


if __name__ == "__main__":
    main()

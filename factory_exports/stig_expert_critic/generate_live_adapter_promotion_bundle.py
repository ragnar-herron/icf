from __future__ import annotations

import json

from live_adapter_promotion import BANNER_BUNDLE_PATH, build_banner_promotion_bundle


def main() -> None:
    bundle = build_banner_promotion_bundle()
    BANNER_BUNDLE_PATH.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(str(BANNER_BUNDLE_PATH))


if __name__ == "__main__":
    main()


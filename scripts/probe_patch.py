"""No-op PATCH probe: re-apply the current banner to confirm write capability."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f5_client import F5Client


def main() -> int:
    client = F5Client()
    before = client.get("/mgmt/tm/sys/global-settings")
    banner = before.get("guiSecurityBannerText")
    if not isinstance(banner, str):
        print("ERROR: banner missing")
        return 1
    print(f"before: len={len(banner)}")

    client.patch("/mgmt/tm/sys/global-settings", {"guiSecurityBannerText": banner})
    print("PATCH ok")

    after = client.get("/mgmt/tm/sys/global-settings")
    banner_after = after.get("guiSecurityBannerText")
    print(f"after:  len={len(banner_after)}")
    print(f"identical: {banner == banner_after}")
    return 0 if banner == banner_after else 2


if __name__ == "__main__":
    raise SystemExit(main())

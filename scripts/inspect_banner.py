"""Read-only probe: print the current guiSecurityBannerText exactly and
report length + SHA-256 so we know what we will need to restore byte-for-byte."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from f5_client import F5Client


def main() -> int:
    client = F5Client()
    data = client.get("/mgmt/tm/sys/global-settings")
    banner = data.get("guiSecurityBannerText")
    if not isinstance(banner, str):
        print("ERROR: guiSecurityBannerText is absent or not a string", file=sys.stderr)
        print(json.dumps(data, indent=2))
        return 1
    digest = hashlib.sha256(banner.encode("utf-8")).hexdigest()
    print(f"hostname: {data.get('hostname')}")
    print(f"tmos_version: {(data.get('selfLink') or '').split('ver=')[-1]}")
    print(f"guiSecurityBanner: {data.get('guiSecurityBanner')}")
    print(f"guiSecurityBannerText length: {len(banner)}")
    print(f"guiSecurityBannerText sha256: {digest}")
    print("guiSecurityBannerText (verbatim, between fences):")
    print("-----BEGIN BANNER-----")
    print(banner)
    print("-----END BANNER-----")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

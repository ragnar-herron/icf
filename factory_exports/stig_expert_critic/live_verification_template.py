from __future__ import annotations

from typing import Any


def live_verification_artifact_template(vid: str, adapter_family: str) -> dict[str, Any]:
    return {
        "adapter_id": f"{adapter_family}:{vid}",
        "control_id": vid,
        "host_refs": [
            "hosts/<validated-host-1>",
            "hosts/<validated-host-2>",
        ],
        "capture_refs": [
            "captures/<verified-live-run-1>",
            "captures/<verified-live-run-2>",
        ],
        "verification_results": {
            "known_good_host": "pass",
            "known_bad_host": "fail",
            "expected_unresolved_host": "projected_unresolved",
        },
        "representation_results": {
            "primary_representation": "pass",
            "alternate_representation": "pass",
        },
        "scope": {
            "platform": "f5-bigip",
            "applies_to": "<declared host or family scope>",
        },
        "live_verification_hash": "<deterministic live verification hash>",
        "status": "live_verified",
    }

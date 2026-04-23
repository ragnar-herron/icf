from __future__ import annotations

from typing import Any


def promotion_artifact_template(vid: str, adapter_family: str) -> dict[str, Any]:
    return {
        "adapter_id": f"{adapter_family}:{vid}",
        "control_id": vid,
        "capture_refs": [
            "captures/<real-device-sample-1>",
            "captures/<real-device-sample-2>",
        ],
        "normalization_map": {
            "<field_name>": "<source extraction mapping>",
        },
        "fixture_results": {
            "good_minimal": "pass",
            "bad_canonical": "fail",
            "bad_representation_variant": "fail",
            "boundary_value": "pass_or_fail",
            "disabled_state": "unresolved_or_fail",
            "absent_state": "unresolved_or_fail",
            "malformed_state": "unresolved_or_fail",
            "noisy_evidence": "pass_or_unresolved",
            "out_of_scope_variant": "projected_unresolved",
        },
        "falsifier_results": {
            "known_bad": "fail",
            "known_good": "pass",
        },
        "replay_hash": "<replay hash from deterministic captured-data replay>",
        "promotion_signature": "<signed promotion record>",
        "status": "promoted",
    }

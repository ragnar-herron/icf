from __future__ import annotations

from typing import Any


CONTROL_RESOLUTION_MAP: dict[str, dict[str, Any]] = {
    "V-266064": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266065": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266066": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266068": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266078": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266079": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266080": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266085": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266092": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266093": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266094": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266167": {
        "resolution_class": "direct_control_support",
        "note": "Promoted standalone control support exists, but this is not a coherent adapter family and should not remain in manual_or_generic.",
    },
    "V-266067": {
        "resolution_class": "external_evidence_required",
        "note": "Appropriate roles and partition access are organization-defined and require external authorization evidence.",
    },
    "V-266074": {
        "resolution_class": "external_evidence_required",
        "note": "Audit storage thresholds are defined by the SSP and require external retention/storage policy evidence.",
    },
    "V-266083": {
        "resolution_class": "manual_attestation_required",
        "note": "Approved certificate policy and approved service provider status require attested issuer approval evidence.",
    },
    "V-266174": {
        "resolution_class": "redesign_required",
        "note": "Always On VPN semantics do not fit the current family model cleanly and should be redesigned rather than promoted under manual_or_generic.",
    },
}

NON_PORTFOLIO_RESOLUTION_CLASSES = {
    "direct_control_support",
    "external_evidence_required",
    "manual_attestation_required",
    "redesign_required",
}


def control_resolution(vuln_id: str) -> dict[str, Any] | None:
    return CONTROL_RESOLUTION_MAP.get(vuln_id)


def resolution_class(vuln_id: str) -> str | None:
    payload = control_resolution(vuln_id)
    return None if payload is None else str(payload.get("resolution_class") or "")


def is_non_portfolio_control(vuln_id: str) -> bool:
    return resolution_class(vuln_id) in NON_PORTFOLIO_RESOLUTION_CLASSES

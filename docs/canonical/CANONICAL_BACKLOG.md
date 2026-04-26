# Canonical Backlog

## Status

STATUS: CANONICAL BACKLOG

Only unresolved work belongs here. Architecture, gate definitions, record schemas, and delivery claims belong in the other canonical documents.

## external_evidence_required

| Item | Controls | Required Resolution |
| --- | --- | --- |
| Audit storage management evidence | V-266074 | Provide organization retention/storage policy package and rerun evidence gate |
| Backup schedule evidence | V-266096 | Provide backup schedule package and combined backup measurable |
| APM consent banner evidence | V-266145 | Provide banner text/policy evidence or promote live policy extraction |
| PKI revocation cache evidence | V-266154 | Provide CRL/OCSP evidence package or promote live extraction |
| Classification/content filtering policy | V-266160 | Provide external classification policy evidence or redesign combined evidence model |

## manual_attestation_required

| Item | Controls | Required Resolution |
| --- | --- | --- |
| Organization-owned policy attestations | Policy-dependent controls | Define provider, validity window, accepted fields, and validation rules for every attestation package |

## adapter_family_promotion

| Item | Controls/Families | Required Resolution |
| --- | --- | --- |
| Reconcile promoted family count | All live adapter families | Resolve "10" vs inventory family count using latest `LiveAdapterPromotionPortfolio` |
| Preserve live tool while enforcing projection gates | web_app/export | Restore live `web_app.py` paths without allowing frontend truth invention |

## redesign_required

| Item | Reason | Required Resolution |
| --- | --- | --- |
| Static projection wrapper replaced live tool expectation | The packaged web app currently says projection-only where users expect live validation | Produce architecture-compliant web app that serves certified projection and live promoted adapter execution under the same support boundary |
| Mixed appliance/external controls | Some controls require both runtime evidence and organizational evidence | Emit combined evidence records or keep controls blocked external |

## release_hardening

| Item | Required Resolution |
| --- | --- |
| Single verification entrypoint | Ensure one script verifies bridge, projection, packaged export, web app smoke, and delivery gate |
| Path normalization | Replace stale `icf_gpt` absolute paths with current workspace-relative or package-relative paths |
| Generated artifact hygiene | Keep generated HTML/bundles reproducible and avoid committing transient pycache/session artifacts unless explicitly intended |

## documentation_cleanup

| Item | Required Resolution |
| --- | --- |
| Mark old docs | Add status headers to markdown/html specs where safe |
| JSON/source input classification | Do not corrupt JSON with prose headers; classify in `SOURCE_DOCUMENT_INDEX.md` instead |
| Blocked-external count conflict | Reconcile older 6 blocked-external campaign docs against latest 5 blocked-external + 2 open release posture |
| Dual C1 namespace | Disambiguate general C1-C7 and STIG C1-C20 in references |

# STIG Expert Critic Standalone Live Export

This folder is the standalone runtime package for the live F5 export app.

Run:

```powershell
python web_app.py
```

Default release scope:

- `supported_only`

To boot the full source catalog anyway:

```powershell
$env:STIG_RELEASE_SCOPE="all"
python web_app.py
```

Verify the standalone boundary locally:

```powershell
python verify_standalone_live_export.py
```

Run the optional live appliance smoke when valid F5 credentials are available:

```powershell
$env:F5_user="admin"
$env:F5_password="..."
python verify_live_f5_smoke.py
```

## Runtime ownership

At runtime this app reads only from this export package plus the connected F5:

- `stig_expert_critic.html`
- `data/*.json`
- `stig_config_lookup/host_list.csv`
- `stig_config_lookup/stig_list.csv`
- `snippets/`
- `residuals/`
- `sessions/`
- live F5 HTTPS responses

It does not import parent factory Python modules and it does not shell out to Cargo.

## Runtime API

The standalone app exposes:

- `GET /`
- `GET /healthz`
- `GET /api/hosts`
- `GET /api/stig_list`
- `GET /api/contracts`
- `GET /api/hydrate/<vid>?host=<host>`
- `POST /api/login` and `POST /api/connect`
- `POST /api/logout` and `POST /api/disconnect`
- `POST /api/tmsh-query`
- `POST /api/rest-query`
- `POST /api/validate`
- `POST /api/validate/all`
- `POST /api/remediate/tmsh`
- `POST /api/remediate/rest`
- `POST /api/residuals/capture`
- `POST /api/verify`
- `POST /api/merge`
- `POST /api/save`
- `GET /api/stig/read/<vid>`
- `POST /api/stig/save/<vid>`

## Current live-evaluator scope

The app is honest about live support:

- shipped in the default supported-only release:
  - `V-266064`
  - `V-266065`
  - `V-266066`
  - `V-266068`
  - `V-266069`
  - `V-266070`
  - `V-266075`
  - `V-266076`
  - `V-266077`
  - `V-266078`
  - `V-266079`
  - `V-266080`
  - `V-266084`
  - `V-266085`
  - `V-266086`
  - `V-266087`
  - `V-266088`
  - `V-266089`
  - `V-266090`
  - `V-266091`
  - `V-266092`
  - `V-266093`
  - `V-266094`
  - `V-266095`
  - `V-266137`
  - `V-266138`
  - `V-266139`
  - `V-266140`
  - `V-266141`
  - `V-266142`
  - `V-266143`
  - `V-266144`
  - `V-266145`
  - `V-266146`
  - `V-266147`
  - `V-266148`
  - `V-266149`
  - `V-266150`
  - `V-266152`
  - `V-266153`
  - `V-266154`
  - `V-266155`
  - `V-266156`
  - `V-266157`
  - `V-266158`
  - `V-266159`
  - `V-266161`
  - `V-266162`
  - `V-266163`
  - `V-266164`
  - `V-266165`
  - `V-266166`
  - `V-266167`
  - `V-266168`
  - `V-266169`
  - `V-266170`
  - `V-266171`
  - `V-266172`
  - `V-266173`
  - `V-266175`
- controls outside that shipped surface remain outside the default release until
  their export-local live evaluators are implemented

`V-266093` and `V-266094` now include explicit PKI/OCSP applicability detection.
On hosts not configured for `Remote - ClientCert LDAP`, they return
`not_applicable` rather than `insufficient_evidence`.

Current supported-only live regression on `132.145.154.175`:

- shipped controls: `60`
- `50` `not_a_finding`
- `8` `open`
- `2` `not_applicable`

Coverage and deliverability records:

- [LiveCoverageInventory.json](C:\work\dev\github\icf_gpt\factory_exports\stig_expert_critic\data\LiveCoverageInventory.json)
- [ClientDeliverabilityGateRecord.json](C:\work\dev\github\icf_gpt\factory_exports\stig_expert_critic\data\ClientDeliverabilityGateRecord.json)

## Operator behavior

- host inventory comes from `stig_config_lookup/host_list.csv`
- control inventory comes from `stig_config_lookup/stig_list.csv`
- host changes clear host-scoped validation state
- snippet load/save stays local to this export folder
- residual capture stays local to this export folder
- merge sequencing stays `verify -> merge -> save`

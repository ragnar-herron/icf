# STIG Expert Critic Factory Export

This export is a standalone local web application for reviewing F5 BIG-IP STIG evidence.

## Run

```powershell
cd factory_exports/stig_expert_critic
$env:STIG_FACTORY_PORT = "8080"
py -3 web_app.py
```

Open the URI printed by `web_app.py`, for example `http://127.0.0.1:8080`.

## Included

- `web_app.py`, `stig_remediation_tool.html`, `f5_client.py`, `live_evaluator.py`
- `data/` with the generated DISA-backed control catalog and live outcome seed data
- `stig_config_lookup/` with host and STIG list CSVs
- `local_policy/authorized_virtual_services.example.json` for target-local PPSM/SSP virtual-service repair inputs
- `snippets/` with small reviewer-editable configuration snippets

## Not Included

The clean export intentionally excludes transient or target-specific artifacts:

- `sessions/`
- `residuals/`
- `bundles/`
- `validate_all/`
- `live_state/`
- `__pycache__/`
- logs and prior local output

Raw residual values and production authorization settings should remain local to the target environment.

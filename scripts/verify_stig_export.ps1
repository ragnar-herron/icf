$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$env:PYTHONIOENCODING = "utf-8"

Write-Output "[1/8] bridge.promote_all"
python -m bridge.promote_all

Write-Output "[2/8] bridge.export_projection"
python -m bridge.export_projection

Write-Output "[3/8] bridge.build_html_export"
python -m bridge.build_html_export

Write-Output "[4/8] bridge.verify_ep_gates"
python -m bridge.verify_ep_gates

Write-Output "[5/8] bridge.shipping_gate"
python -m bridge.shipping_gate

Write-Output "[6/8] bridge.build_packaged_web_app"
python -m bridge.build_packaged_web_app

Write-Output "[7/8] bridge.verify_packaged_export"
python -m bridge.verify_packaged_export

Write-Output "[8/8] packaged app smoke test"
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "smoke_packaged_web_app.ps1")

Write-Output "STIG EXPORT VERIFICATION: PASS"

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$packageRoot = Join-Path $repoRoot "factory_exports\stig_expert_critic"
$liveWebApp = Join-Path $packageRoot "web_app_live.py"
$projectionWebApp = Join-Path $packageRoot "web_app_projection.py"

$env:STIG_FACTORY_BIND = "127.0.0.1"
$env:STIG_FACTORY_PORT = "8016"
$env:STIG_EXPORT_HOST = "127.0.0.1"
$env:STIG_EXPORT_PORT = "8017"

$liveJob = Start-Job -ScriptBlock {
    param($root, $webAppPath)
    Set-Location $root
    python $webAppPath --mode live
} -ArgumentList $packageRoot, $liveWebApp

$projectionJob = Start-Job -ScriptBlock {
    param($root, $webAppPath)
    Set-Location $root
    python $webAppPath --mode projection
} -ArgumentList $packageRoot, $projectionWebApp

try {
    Start-Sleep -Seconds 2

    $hostsResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8016/api/hosts" -UseBasicParsing
    try {
        $liveValidateResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8016/api/validate" -Method Post -Body "{}" -ContentType "application/json" -UseBasicParsing
    }
    catch {
        $liveValidateResponse = $_.Exception.Response
    }

    $rootResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8017/" -UseBasicParsing
    $projectionResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8017/api/projection_bundle" -UseBasicParsing
    $healthResponse = Invoke-WebRequest -Uri "http://127.0.0.1:8017/healthz" -UseBasicParsing
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8017/api/validate" -Method Post -Body "{}" -ContentType "application/json" -UseBasicParsing | Out-Null
        throw "projection mode allowed /api/validate"
    }
    catch {
        $projectionValidateStatus = [int]$_.Exception.Response.StatusCode
    }

    $projection = ConvertFrom-Json $projectionResponse.Content
    $hosts = ConvertFrom-Json $hostsResponse.Content
    if ($hostsResponse.StatusCode -ne 200) {
        throw "live /api/hosts did not return 200"
    }
    if ($hosts.Count -lt 1) {
        throw "live /api/hosts did not return machines from stig_config_lookup/host_list.csv"
    }
    if ($hosts[0].host -ne "132.145.154.175" -or $hosts[0].label -ne "bigip1") {
        throw "live /api/hosts did not reflect stig_config_lookup/host_list.csv"
    }
    if ([int]$liveValidateResponse.StatusCode -eq 404) {
        throw "live /api/validate route is missing"
    }
    if ($rootResponse.StatusCode -ne 200) {
        throw "projection root endpoint did not return 200"
    }
    if ($projectionResponse.StatusCode -ne 200) {
        throw "projection endpoint did not return 200"
    }
    if ($healthResponse.StatusCode -ne 200) {
        throw "health endpoint did not return 200"
    }
    if ($projection.Count -ne 67) {
        throw "projection endpoint did not return 67 entries"
    }
    if ($projectionValidateStatus -ne 403) {
        throw "projection /api/validate did not block live execution"
    }

    Write-Output "PACKAGED APP SMOKE: PASS"
    Write-Output "LIVE_HOSTS_STATUS=$($hostsResponse.StatusCode)"
    Write-Output "LIVE_HOSTS_COUNT=$($hosts.Count)"
    Write-Output "LIVE_FIRST_HOST=$($hosts[0].host)"
    Write-Output "LIVE_FIRST_LABEL=$($hosts[0].label)"
    Write-Output "LIVE_VALIDATE_STATUS=$([int]$liveValidateResponse.StatusCode)"
    Write-Output "PROJECTION_ROOT_STATUS=$($rootResponse.StatusCode)"
    Write-Output "PROJECTION_API_STATUS=$($projectionResponse.StatusCode)"
    Write-Output "PROJECTION_HEALTH_STATUS=$($healthResponse.StatusCode)"
    Write-Output "PROJECTION_API_COUNT=$($projection.Count)"
    Write-Output "PROJECTION_VALIDATE_STATUS=$projectionValidateStatus"
}
finally {
    Stop-Job $liveJob, $projectionJob -ErrorAction SilentlyContinue | Out-Null
    Remove-Job $liveJob, $projectionJob -Force -ErrorAction SilentlyContinue | Out-Null
}

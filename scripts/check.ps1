param(
    [switch]$SkipFmt
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$RustupCargo = Join-Path $env:USERPROFILE ".cargo\bin\cargo.exe"
$CargoCommand = Get-Command cargo -ErrorAction SilentlyContinue
if (Test-Path $RustupCargo) {
    $Cargo = $RustupCargo
} elseif ($CargoCommand) {
    $Cargo = $CargoCommand.Source
} else {
    $Cargo = $RustupCargo
}

if (-not (Test-Path $Cargo)) {
    throw "cargo was not found on PATH or at $Cargo"
}

$CargoBin = Split-Path -Parent $Cargo
$env:PATH = "$CargoBin;$env:PATH"
$Rustfmt = Join-Path $CargoBin "rustfmt.exe"

function Invoke-Cargo {
    Write-Host "> cargo $args"
    & $Cargo @args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

function Invoke-RustfmtCheck {
    if (-not (Test-Path $Rustfmt)) {
        throw "rustfmt was not found at $Rustfmt"
    }

    $RustFiles = Get-ChildItem -Path src, tests -Filter *.rs -Recurse | ForEach-Object { $_.FullName }
    Write-Host "> rustfmt --check src tests"
    & $Rustfmt --check @RustFiles
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if (-not $SkipFmt) {
    Invoke-RustfmtCheck
}

Invoke-Cargo check
Invoke-Cargo test
Invoke-Cargo run -- demo p0a
Invoke-Cargo run -- ledger verify ledgers\demo\p0a.jsonl
Invoke-Cargo run -- demo break-fix
Invoke-Cargo run -- ledger verify ledgers\demo\break_fix.jsonl
Invoke-Cargo run -- coalgebra report --fail-on-missing-core
Invoke-Cargo run -- distinction report --fail-on-regression
Invoke-Cargo run -- distinction stig-report --fail-on-regression
Invoke-Cargo run -- maturity verify-fixture fixtures\maturity
Invoke-Cargo run -- maturity report
Invoke-Cargo run -- maturity report --fail-on-partial

# Live evidence replay: hermetic (no network). Re-verifies that the captured
# live ledger (ledgers\live\break_fix.jsonl) still rebuilds byte-for-byte
# from the committed blobs in blobstore\live\ and the committed manifest.
Invoke-Cargo run -- ledger verify ledgers\live\break_fix.jsonl
Invoke-Cargo run -- ledger verify ledgers\live\full_campaign.jsonl

$Py = Join-Path $env:WINDIR "py.exe"
if (-not (Test-Path $Py)) {
    $PyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($PyCommand) {
        $Py = $PyCommand.Source
    }
}
if (-not (Test-Path $Py)) {
    throw "Python launcher was not found at $Py"
}
Write-Host "> py -3 -B scripts\compare_assertion_contracts.py"
& $Py -3 -B scripts\compare_assertion_contracts.py
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host "P0a coalgebra bootstrap + live replay checks passed."

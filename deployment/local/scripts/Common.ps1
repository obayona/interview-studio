$ErrorActionPreference = "Stop"
$Script:LocalRoot = Split-Path -Parent $PSScriptRoot
$Script:EnvFile = Join-Path $Script:LocalRoot ".env.local"
$Script:ComposeFile = Join-Path $Script:LocalRoot "compose.yml"

function Get-LocalEnvironment {
    if (-not (Test-Path $Script:EnvFile)) {
        Copy-Item (Join-Path $Script:LocalRoot ".env.example") $Script:EnvFile
        Write-Host "Created $Script:EnvFile with safe local defaults."
    }
    $values = @{}
    foreach ($line in Get-Content $Script:EnvFile) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) { continue }
        $parts = $trimmed.Split("=", 2)
        if ($parts.Count -ne 2) { throw "Invalid assignment in .env.local: $line" }
        $values[$parts[0].Trim()] = $parts[1].Trim().Trim('"').Trim("'")
    }
    if ($values.APP_VERSION -notmatch '^\d+\.\d+\.\d+$') {
        throw "APP_VERSION must be a semantic version such as 1.0.0."
    }
    $port = 0
    if (-not [int]::TryParse($values.LOCAL_PORT, [ref]$port) -or $port -lt 1024 -or $port -gt 65535) {
        throw "LOCAL_PORT must be an integer from 1024 through 65535."
    }
    if ([string]::IsNullOrWhiteSpace($values.BACKUP_DIR)) {
        throw "BACKUP_DIR cannot be empty."
    }
    if (-not [IO.Path]::IsPathRooted($values.BACKUP_DIR)) {
        $values.BACKUP_DIR = [IO.Path]::GetFullPath((Join-Path $Script:LocalRoot $values.BACKUP_DIR))
    }
    New-Item -ItemType Directory -Force -Path $values.BACKUP_DIR | Out-Null
    $probe = Join-Path $values.BACKUP_DIR ".interview-studio-write-test"
    try {
        [IO.File]::WriteAllText($probe, "test")
        Remove-Item $probe
    } catch {
        throw "BACKUP_DIR is not writable: $($values.BACKUP_DIR)"
    }
    $env:BACKUP_DIR = $values.BACKUP_DIR
    $env:LOCAL_BACKUP_UID = "0"
    $env:LOCAL_BACKUP_GID = "0"
    if (Get-Command id -ErrorAction SilentlyContinue) {
        $env:LOCAL_BACKUP_UID = (& id -u).Trim()
        $env:LOCAL_BACKUP_GID = (& id -g).Trim()
    }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) { throw "Docker with Compose v2 is required." }
    return $values
}

function Invoke-LocalCompose {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArguments)
    & docker compose --env-file $Script:EnvFile -f $Script:ComposeFile @ComposeArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed: $($ComposeArguments -join ' ')"
    }
}

function Wait-LocalReady {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        & docker compose --env-file $Script:EnvFile -f $Script:ComposeFile exec -T backend `
            python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=3)" 2>$null
        if ($LASTEXITCODE -eq 0) { return }
        Start-Sleep -Seconds 1
    }
    Invoke-LocalCompose ps
    throw "Interview Studio did not become ready within 60 seconds."
}

function Set-LocalVersion {
    param([Parameter(Mandatory = $true)][string]$Version)
    if ($Version -notmatch '^\d+\.\d+\.\d+$') {
        throw "Version must use semantic form such as 1.0.1."
    }
    $lines = Get-Content $Script:EnvFile
    $found = $false
    $updated = foreach ($line in $lines) {
        if ($line -match '^APP_VERSION=') {
            $found = $true
            "APP_VERSION=$Version"
        } else {
            $line
        }
    }
    if (-not $found) { $updated += "APP_VERSION=$Version" }
    $updated | Set-Content -Encoding utf8 $Script:EnvFile
}

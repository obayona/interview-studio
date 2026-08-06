param([Parameter(Mandatory = $true)][string]$BackupName)
. (Join-Path $PSScriptRoot "Common.ps1")
if ($BackupName -notmatch '^\d{8}T\d{6}Z$') { throw "Backup name must be a generated UTC timestamp." }
Get-LocalEnvironment | Out-Null
try {
    Invoke-LocalCompose stop backend
    Invoke-LocalCompose --profile tools run --rm restore `
        python -m backend.cli.deployment_data restore --source "/backups/$BackupName"
    Invoke-LocalCompose --profile tools run --rm migrate
    Invoke-LocalCompose up -d backend
    Wait-LocalReady
} catch {
    try { Invoke-LocalCompose up -d backend } catch { Write-Warning $_ }
    throw
}
Write-Host "Backup $BackupName restored."

param([string]$Version)
. (Join-Path $PSScriptRoot "Common.ps1")
$environment = Get-LocalEnvironment
$previousVersion = $environment.APP_VERSION
Invoke-LocalCompose --profile tools run --rm backup
if ($Version) {
    Set-LocalVersion $Version
    $environment.APP_VERSION = $Version
}
Invoke-LocalCompose pull backend web
try {
    Invoke-LocalCompose stop backend web
    Invoke-LocalCompose --profile tools run --rm migrate
    Invoke-LocalCompose --profile tools run --rm fixtures
    Invoke-LocalCompose up -d --force-recreate backend web
    Wait-LocalReady
} catch {
    if ($environment.APP_VERSION -ne $previousVersion) {
        Set-LocalVersion $previousVersion
    }
    try { Invoke-LocalCompose up -d backend web } catch { Write-Warning $_ }
    throw
}
Write-Host "Interview Studio $($environment.APP_VERSION) is ready."

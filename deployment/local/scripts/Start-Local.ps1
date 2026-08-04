. (Join-Path $PSScriptRoot "Common.ps1")
$environment = Get-LocalEnvironment
Invoke-LocalCompose pull backend web
$running = & docker compose --env-file $Script:EnvFile -f $Script:ComposeFile ps -q web
if (-not $running) {
    & docker compose --env-file $Script:EnvFile -f $Script:ComposeFile --profile tools run --rm --service-ports port-check
    if ($LASTEXITCODE -ne 0) {
        throw "LOCAL_PORT $($environment.LOCAL_PORT) is already in use. Change it in .env.local."
    }
}
Invoke-LocalCompose --profile tools run --rm migrate
Invoke-LocalCompose --profile tools run --rm fixtures
Invoke-LocalCompose up -d backend web
Wait-LocalReady
$url = "http://localhost:$($environment.LOCAL_PORT)"
Start-Process $url
Write-Host "Interview Studio is ready at $url"

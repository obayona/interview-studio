. (Join-Path $PSScriptRoot "Common.ps1")
Get-LocalEnvironment | Out-Null
Invoke-LocalCompose --profile tools run --rm backup

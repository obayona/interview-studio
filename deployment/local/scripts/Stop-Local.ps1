. (Join-Path $PSScriptRoot "Common.ps1")
Get-LocalEnvironment | Out-Null
Invoke-LocalCompose down
Write-Host "Interview Studio stopped. Local data was retained."

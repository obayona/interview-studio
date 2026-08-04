param([switch]$DeleteData)
. (Join-Path $PSScriptRoot "Common.ps1")
Get-LocalEnvironment | Out-Null
if (-not $DeleteData) {
    Invoke-LocalCompose down --remove-orphans --rmi all
    Write-Host "Interview Studio containers and images were removed. Local data was retained."
    exit 0
}
$confirmation = Read-Host "Type DELETE to permanently remove every local profile, interview, report, and setting"
if ($confirmation -ne "DELETE") {
    throw "Data deletion cancelled."
}
Invoke-LocalCompose down --volumes --remove-orphans --rmi all
Write-Host "Interview Studio and its local data were removed. This cannot be undone."

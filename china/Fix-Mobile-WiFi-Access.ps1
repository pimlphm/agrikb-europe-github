param(
  [int]$Port = 8010
)

$ErrorActionPreference = "Stop"
$ruleName = "AgriKB Mobile WiFi TCP $Port"

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  $script = "`"$PSCommandPath`" -Port $Port"
  Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File $script" -Verb RunAs
  exit
}

$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
  New-NetFirewallRule `
    -DisplayName $ruleName `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort $Port `
    -Profile Public,Private `
    -RemoteAddress LocalSubnet `
    -Description "Allow trusted phones on the same local subnet to access AgriKB on TCP $Port." | Out-Null
} else {
  Set-NetFirewallRule -DisplayName $ruleName -Enabled True -Action Allow -Profile Public,Private | Out-Null
  $rule = Get-NetFirewallRule -DisplayName $ruleName
  Set-NetFirewallPortFilter -AssociatedNetFirewallRule $rule -Protocol TCP -LocalPort $Port | Out-Null
  Set-NetFirewallAddressFilter -AssociatedNetFirewallRule $rule -RemoteAddress LocalSubnet | Out-Null
}

Write-Host ""
Write-Host "AgriKB mobile Wi-Fi access rule is enabled." -ForegroundColor Green
Write-Host "Phone URL: http://10.188.88.114:$Port/ui/" -ForegroundColor Cyan
Write-Host ""
Write-Host "If the phone still cannot open it on hotel Wi-Fi, the hotel router likely blocks device-to-device traffic." -ForegroundColor Yellow
Write-Host "Use a phone hotspot, a private router, or a public tunnel in that case."
Write-Host ""
Read-Host "Press Enter to close"

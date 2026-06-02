param(
  [int]$Port = 8010,
  [int]$TtsPort = 8011
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
  Write-Host "AgriKB setup is incomplete. Please run Setup-NewComputer.ps1 first." -ForegroundColor Red
  exit 1
}

$ip = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -notlike "127.*" -and
    $_.IPAddress -notlike "169.254.*" -and
    $_.InterfaceAlias -notmatch "tap|virtual|loopback|vmware|vbox|bluetooth" -and
    $_.AddressState -eq "Preferred"
  } |
  Sort-Object -Property InterfaceMetric |
  Select-Object -First 1 -ExpandProperty IPAddress

if (-not $ip) {
  $ip = "127.0.0.1"
}

$desktopUrl = "http://127.0.0.1:$Port/ui/?v=20260525agri93"
$mobileUrl = "http://$ip`:$Port/ui/?v=20260525agri93"

Write-Host ""
Write-Host "AgriKB mobile QR test mode" -ForegroundColor Green
Write-Host "Desktop URL: $desktopUrl"
Write-Host "Mobile URL : $mobileUrl" -ForegroundColor Cyan
Write-Host "Voice input has been removed. Answers can still be read aloud with the speaker button." -ForegroundColor Yellow
Write-Host "Use the same Wi-Fi on phone and PC. If the phone cannot open it, allow Python or TCP port $Port in Windows Firewall."
Write-Host ""

@($Port, $TtsPort) | ForEach-Object {
  $listenPort = $_
  Get-NetTCPConnection -LocalPort $listenPort -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
  $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
  if ($process) {
    Stop-Process -Id $process.Id -Force
  }
  }
}

Start-Process -FilePath $Python `
  -ArgumentList @("tools\tts_daemon.py", "--host", "127.0.0.1", "--port", "$TtsPort") `
  -WorkingDirectory $Root `
  -WindowStyle Hidden

Start-Process -FilePath $Python `
  -ArgumentList @("-m", "uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "$Port") `
  -WorkingDirectory $Root `
  -WindowStyle Hidden

Start-Sleep -Seconds 4
Start-Process $desktopUrl

Write-Host "Server started. Open the desktop URL on this PC, or scan the QR code for phone screen testing." -ForegroundColor Green

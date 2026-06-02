param(
    [switch]$NoBrowser,
    [switch]$ForceApiBackend,
    [int]$TtsPort = 8011
)

$ErrorActionPreference = "Stop"
$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

function Read-DotEnv([string]$Path) {
    $values = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $values }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $key, $value = $line.Split("=", 2)
        $values[$key.Trim()] = $value.Trim().Trim('"').Trim("'")
    }
    return $values
}

function Test-AgriKBUvicornProcess([int]$ProcessId) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        $commandLine = [string]$proc.CommandLine
        return ($commandLine -match "uvicorn" -and $commandLine -match "src\.backend\.app:app")
    } catch {
        return $false
    }
}

function Test-StaleKimiCodingService([string]$HealthUrl, [bool]$ExpectKimiCli) {
    if (-not $ExpectKimiCli) { return $false }
    try {
        $health = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 4
        return ($health.status -eq "ok" -and [string]$health.active_provider -ne "KimiCliProvider")
    } catch {
        return $false
    }
}

$venvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$setupArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $RootDir "Setup-NewComputer.ps1"))
if (Test-Path -LiteralPath $venvPython) {
    $setupArgs += "-NoInstall"
}
if ($ForceApiBackend) {
    $setupArgs += "-ForceApiBackend"
}
& powershell @setupArgs

$doctorPath = Join-Path $RootDir "Invoke-EnvDoctor.ps1"
if (Test-Path -LiteralPath $doctorPath) {
    . $doctorPath -InstallMissing
}

$envValues = Read-DotEnv (Join-Path $RootDir ".env")
foreach ($key in $envValues.Keys) {
    if ($key -and $envValues[$key]) {
        [Environment]::SetEnvironmentVariable($key, [string]$envValues[$key], "Process")
    }
}
if (-not $env:KIMI_API_KEY -and $env:KNOWLEDGE_RAG_API_KEY) {
    $env:KIMI_API_KEY = $env:KNOWLEDGE_RAG_API_KEY
}
$kimiBin = Join-Path $RootDir "runtime\kimi"
$kimiRgBin = Join-Path $RootDir "runtime\kimi\opencode\bin"
if (Test-Path -LiteralPath $kimiBin) {
    $env:PATH = "$kimiBin;$kimiRgBin;$env:PATH"
}
$venvPython = if ($env:AGRIKB_RESOLVED_PYTHON -and (Test-Path -LiteralPath $env:AGRIKB_RESOLVED_PYTHON)) { $env:AGRIKB_RESOLVED_PYTHON } else { $venvPython }
$BindHost = if ($env:KNOWLEDGE_RAG_HOST) { $env:KNOWLEDGE_RAG_HOST } elseif ($envValues["KNOWLEDGE_RAG_HOST"]) { $envValues["KNOWLEDGE_RAG_HOST"] } else { "127.0.0.1" }
$BindPort = if ($env:KNOWLEDGE_RAG_PORT) { $env:KNOWLEDGE_RAG_PORT } elseif ($envValues["KNOWLEDGE_RAG_PORT"]) { $envValues["KNOWLEDGE_RAG_PORT"] } else { "8010" }
$OpenHost = if ($BindHost -in @("0.0.0.0", "::")) { "127.0.0.1" } else { $BindHost }
$url = "http://${OpenHost}:${BindPort}/ui/"
$expectsKimiCli = ($env:KIMI_API_KEY -like "sk-kimi-*") -or ($env:KNOWLEDGE_RAG_API_KEY -like "sk-kimi-*") -or ($env:KNOWLEDGE_RAG_BASE_URL -like "*api.kimi.com/coding*") -or ($env:KNOWLEDGE_RAG_MODEL -eq "kimi-for-coding")

$ttsExisting = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::") -and $_.LocalPort -eq $TtsPort } |
    Select-Object -First 1
if (-not $ttsExisting) {
    Start-Process -FilePath $venvPython `
        -ArgumentList @("tools\tts_daemon.py", "--host", "127.0.0.1", "--port", "$TtsPort") `
        -WorkingDirectory $RootDir `
        -WindowStyle Hidden
}

$existing = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
    Where-Object { $_.LocalAddress -in @($BindHost, "127.0.0.1", "0.0.0.0", "::") -and $_.LocalPort -eq [int]$BindPort } |
    Select-Object -First 1

if ($existing) {
    $healthUrl = "http://${OpenHost}:${BindPort}/health"
    $isStaleKimiService = Test-StaleKimiCodingService $healthUrl $expectsKimiCli
    if ($isStaleKimiService -and (Test-AgriKBUvicornProcess ([int]$existing.OwningProcess))) {
        Write-Host "Detected an old AgriKB service on port $BindPort; restarting it with the bundled Kimi CLI runtime." -ForegroundColor Yellow
        Stop-Process -Id ([int]$existing.OwningProcess) -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    } else {
        Write-Host "AgriKB service is already listening at $url (PID $($existing.OwningProcess))." -ForegroundColor Green
        if (-not $NoBrowser) { Start-Process $url }
        return
    }
}

if (-not $NoBrowser) {
    Start-Process $url
}

Write-Host "AgriKB service starting at $url" -ForegroundColor Green
& $venvPython -m uvicorn src.backend.app:app --host $BindHost --port $BindPort
